from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # CORS — comma-separated origins, e.g. http://localhost:5173,https://app.vercel.app
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Translation via LLM: openai (Chat Completions) | anthropic (Claude Messages)
    translation_provider: str = "openai"
    openai_translation_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_translation_model: str = "claude-3-5-haiku-20241022"
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_version: str = "2023-06-01"

    # Embeddings: openai | gemini
    embedding_provider: str = "openai"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_base_url: str = "https://api.openai.com/v1"

    gemini_api_key: str = ""
    gemini_embedding_model: str = "text-embedding-004"

    max_input_chars: int = 800


@lru_cache
def get_settings() -> Settings:
    return Settings()
