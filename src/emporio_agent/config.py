from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="EMPORIO_",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = None
    model: str = "gpt-4.1-mini"
    log_level: str = "INFO"
    max_tool_rounds: int = Field(default=4, ge=1, le=8)
    max_tool_calls: int = Field(default=8, ge=1, le=16)
    artifacts_dir: Path = PROJECT_ROOT / "artefatos_projeto"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"

    @property
    def database_path(self) -> Path:
        return self.processed_dir / "emporio.db"

    @property
    def policy_index_path(self) -> Path:
        return self.processed_dir / "policy_chunks.json"

    @property
    def policy_pdf_path(self) -> Path:
        return self.artifacts_dir / "políticas_da_loja.pdf"


@lru_cache
def get_settings() -> Settings:
    return Settings()
