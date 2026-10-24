from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    max_tokens: int = 1024

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173"

    # --- RAG ---
    database_url: str = "postgresql://postgres:postgres@localhost:5433/chatbot"
    # Never change these two without re-uploading all documents (old vectors won't match)
    embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 768
    chunk_size: int = 1000  # max characters per chunk
    chunk_overlap: int = 200  # characters repeated from the previous chunk
    max_upload_mb: int = 10
    top_k: int = 5  # how many chunks to send to the LLM per question
    min_score: float = 0.5  # ignore chunks less similar than this (0 to 1)


settings = Settings()
