from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="BILLING_")

    secret_key: SecretStr = SecretStr("demo-secret")
    provider_api_key: SecretStr | None = None
