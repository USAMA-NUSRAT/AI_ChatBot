import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import vector_store
from app.config import settings
from app.documents import SUPPORTED_EXTENSIONS, DocumentError, extract_text, split_text
from app.embeddings import embed_texts
from app.llm import ProviderError, chat
from app.prompts import RAG_SYSTEM_PROMPT, build_rag_message

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts: make sure the tables exist
    await vector_store.init_db()
    yield
    # Runs once when the server stops
    await vector_store.close_db()


app = FastAPI(title="Simple Chatbot API", lifespan=lifespan)

logger = logging.getLogger(__name__)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)


class Source(BaseModel):
    filename: str
    chunk_index: int
    score: float
    content: str


class ChatResponse(BaseModel):
    reply: str
    provider: str
    sources: list[Source]


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---------- Chat (RAG phase 2: question -> search -> answer) ----------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    messages = [m.model_dump() for m in req.messages]
    if messages[-1]["role"] != "user":
        raise HTTPException(400, "The last message must be from the user")
    question = messages[-1]["content"]

    # 1. Search text: include the previous question so follow-ups like
    #    "and for sick leave?" still find the right chunks
    previous = [m["content"] for m in messages[:-1] if m["role"] == "user"]
    search_text = f"{previous[-1]}\n{question}" if previous else question

    # 2. Find the most similar chunks in pgvector
    try:
        [query_vector] = await embed_texts([search_text], task_type="RETRIEVAL_QUERY")
    except Exception as exc:
        logger.exception("Embedding the question failed")
        raise HTTPException(502, f"Embedding failed: {exc}")
    chunks = await vector_store.search(query_vector, settings.top_k, settings.min_score)
    logger.info("Question %r -> %d chunks, scores: %s",
                question, len(chunks), [round(c["score"], 3) for c in chunks])

    # 3. Replace the last message with "documents + question";
    #    earlier messages stay as they are, so the conversation keeps its memory
    messages[-1] = {"role": "user", "content": build_rag_message(question, chunks)}

    # 4. Ask the LLM (system prompt = the rules)
    try:
        reply, provider = await chat(messages, system=RAG_SYSTEM_PROMPT)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return ChatResponse(reply=reply, provider=provider, sources=chunks)


# ---------- Documents (RAG phase 1: upload -> chunk -> embed -> store) ----------

class DocumentInfo(BaseModel):
    id: int
    filename: str
    chunk_count: int
    uploaded_at: datetime


@app.post("/api/documents", response_model=DocumentInfo)
async def upload_document(file: UploadFile):
    filename = file.filename or ""
    if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}")

    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"File is larger than {settings.max_upload_mb} MB")

    # 1. Read the text
    try:
        text = extract_text(filename, data)
        logger.info("after extract text: %d chars, starts with: %s", len(text), text[:700])

    except DocumentError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.exception("Could not read %s", filename)
        raise HTTPException(400, f"Could not read the file: {exc}")

    # 2. Split into chunks
    chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
    logger.info("%s: %d characters -> %d chunks", filename, len(text), len(chunks))

    # 3. Turn each chunk into a vector
    try:
        vectors = await embed_texts(chunks, task_type="RETRIEVAL_DOCUMENT")
    except Exception as exc:
        logger.exception("Embedding failed for %s", filename)
        raise HTTPException(502, f"Embedding failed: {exc}")

    # 4. Store chunks + vectors in pgvector
    return await vector_store.save_document(filename, chunks, vectors)


@app.get("/api/documents", response_model=list[DocumentInfo])
async def get_documents():
    return await vector_store.list_documents()


@app.delete("/api/documents/{document_id}")
async def remove_document(document_id: int):
    if not await vector_store.delete_document(document_id):
        raise HTTPException(404, "Document not found")
    return {"deleted": document_id}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # restart automatically when code changes
        reload_dirs=[str(Path(__file__).resolve().parent)],
    )
