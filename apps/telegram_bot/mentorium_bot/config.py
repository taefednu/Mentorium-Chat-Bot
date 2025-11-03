from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="BOT_")

    telegram_token: SecretStr
    openai_api_key: SecretStr

    report_period: str = "текущую неделю"
