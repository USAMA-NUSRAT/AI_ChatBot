"""Store documents and their chunk embeddings in PostgreSQL (pgvector)."""

import asyncpg
from pgvector.asyncpg import register_vector

from .config import settings

# A pool keeps a few connections open and reuses them, instead of
# connecting to the database again on every request
_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    """Create the extension, tables and index if missing, then open the pool."""
    global _pool

    # The extension must exist before register_vector can find the vector type
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id          SERIAL PRIMARY KEY,
                filename    TEXT NOT NULL UNIQUE,
                chunk_count INTEGER NOT NULL,
                uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id          SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content     TEXT NOT NULL,
                embedding   VECTOR({settings.embedding_dim}) NOT NULL
            )
        """)
        # HNSW index makes similarity search fast as the table grows
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx
            ON chunks USING hnsw (embedding vector_cosine_ops)
        """)
    finally:
        await conn.close()

    # register_vector teaches asyncpg how to send/receive the vector type
    _pool = await asyncpg.create_pool(settings.database_url, init=register_vector)


async def close_db() -> None:
    if _pool:
        await _pool.close()


async def save_document(filename: str, chunks: list[str], vectors: list[list[float]]) -> dict:
    """Save a document and its chunks. Re-uploading the same filename replaces it."""
    async with _pool.acquire() as conn:
        async with conn.transaction():
            # ON DELETE CASCADE removes the old chunks too
            await conn.execute("DELETE FROM documents WHERE filename = $1", filename)
            doc = await conn.fetchrow(
                """INSERT INTO documents (filename, chunk_count) VALUES ($1, $2)
                   RETURNING id, filename, chunk_count, uploaded_at""",
                filename, len(chunks),
            )
            await conn.executemany(
                "INSERT INTO chunks (document_id, chunk_index, content, embedding) VALUES ($1, $2, $3, $4)",
                [(doc["id"], i, chunk, vec) for i, (chunk, vec) in enumerate(zip(chunks, vectors))],
            )
    return dict(doc)


async def search(query_vector: list[float], top_k: int, min_score: float) -> list[dict]:
    """Return the chunks most similar to the query vector, best first.

    `<=>` is pgvector's cosine distance (0 = same meaning), so
    similarity score = 1 - distance (1 = same meaning).
    """
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT d.filename, c.chunk_index, c.content,
                      1 - (c.embedding <=> $1) AS score
               FROM chunks c
               JOIN documents d ON d.id = c.document_id
               ORDER BY c.embedding <=> $1
               LIMIT $2""",
            query_vector, top_k,
        )
    return [dict(r) for r in rows if r["score"] >= min_score]


async def list_documents() -> list[dict]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, filename, chunk_count, uploaded_at FROM documents ORDER BY uploaded_at DESC"
        )
    return [dict(r) for r in rows]


async def delete_document(document_id: int) -> bool:
    async with _pool.acquire() as conn:
        result = await conn.execute("DELETE FROM documents WHERE id = $1", document_id)
    return result != "DELETE 0"
