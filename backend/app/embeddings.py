"""Turn text into embedding vectors with Gemini."""

from google import genai
from google.genai import types as genai_types

from .config import settings

BATCH_SIZE = 100  # max texts per Gemini request


async def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    """Return one vector per text.

    task_type is "RETRIEVAL_DOCUMENT" for chunks being stored and
    "RETRIEVAL_QUERY" for a user's question.
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (needed for embeddings)")

    client = genai.Client(api_key=settings.gemini_api_key)
    config = genai_types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=settings.embedding_dim,
    )

    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        # Each text must be its own Content; a plain list of strings is
        # merged into a single embedding by gemini-embedding-2
        contents = [genai_types.Content(parts=[genai_types.Part(text=t)]) for t in batch]
        response = await client.aio.models.embed_content(
            model=settings.embedding_model,
            contents=contents,
            config=config,
        )
        vectors.extend(e.values for e in response.embeddings)

    if len(vectors) != len(texts):
        raise RuntimeError(f"Expected {len(texts)} embeddings, got {len(vectors)}")
    return vectors
