from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from mentorium_ai_client import MentoriumAIClient

from .config import BotSettings

_settings = BotSettings()


def create_bot() -> Bot:
    return Bot(token=_settings.telegram_token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_ai_client() -> MentoriumAIClient:
    return MentoriumAIClient(api_key=_settings.openai_api_key.get_secret_value())
