"""Prompts for the RAG chatbot."""

RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about the user's uploaded documents.

Rules:
- Answer using ONLY the information inside the <documents> section of the user's latest message.
- If the answer is not in the documents, reply: "I couldn't find this in the uploaded documents." Do not guess and do not use outside knowledge.
- For greetings or small talk (like "hello" or "thanks"), reply briefly and invite the user to ask about the documents.
- Keep answers short and clear. Use a bullet list when there are several items.
- Do not mention "chunks", "context" or "documents section"; just answer naturally."""


def build_rag_message(question: str, chunks: list[dict]) -> str:
    """Combine the retrieved chunks and the user's question into one message."""
    if chunks:
        docs = "\n".join(
            f'<document index="{i}" source="{c["filename"]}">\n{c["content"]}\n</document>'
            for i, c in enumerate(chunks, start=1)
        )
    else:
        docs = "(no relevant documents found)"
    return f"<documents>\n{docs}\n</documents>\n\nQuestion: {question}"
