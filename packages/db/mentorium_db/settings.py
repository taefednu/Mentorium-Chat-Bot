from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Find the root directory (where .env is located)
def find_root_dir() -> Path:
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".env").exists():
            return current
        current = current.parent
    return Path.cwd()


ROOT_DIR = find_root_dir()


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    bot_db_url: str = "postgresql+psycopg://mentorium:mentorium_dev_pass@localhost:5432/mentorium_bot"
    platform_db_url: str = "postgresql+psycopg://readonly_user:password@db.mentorium.uz:5432/mentorium_platform"

    @property
    def url(self) -> str:
        """Main bot database URL (for Alembic and bot operations)"""
        return self.bot_db_url

    @property
    def async_url(self) -> str:
        """Async version of bot database URL"""
        url = self.bot_db_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        return url
    
    @property
    def platform_async_url(self) -> str:
        """Async version of platform database URL (read-only)"""
        url = self.platform_db_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        return url
