from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_root_dir() -> Path:
    """Найти корневую директорию проекта (где находится .env)"""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".env").exists():
            return current
        current = current.parent
    return Path.cwd()


ROOT_DIR = find_root_dir()


class ReportingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        env_prefix="REPORT_",
        extra="ignore",
    )

    timezone: str = "Europe/Moscow"
    schedule_cron: str = "0 18 * * *"
    openai_api_key: SecretStr
