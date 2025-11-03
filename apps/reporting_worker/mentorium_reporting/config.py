from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReportingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="REPORT_")

    timezone: str = "Europe/Moscow"
    schedule_cron: str = "0 18 * * *"
    openai_api_key: SecretStr
