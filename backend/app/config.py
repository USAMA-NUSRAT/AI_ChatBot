from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    system_prompt: str = "You are a helpful, friendly assistant."
    max_tokens: int = 1024

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173"


settings = Settings()
