"""Middleware для инжекции зависимостей в handlers"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DependencyInjectionMiddleware(BaseMiddleware):
    """
    Middleware для инжекции AI client и других зависимостей в handlers
    
    Получает зависимости из dispatcher workflow_data и добавляет в handler kwargs
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Получаем ai_client из workflow_data
        workflow_data = data.get("event_from_user") or data.get("event_update")
        if workflow_data:
            dp = workflow_data.bot.dispatcher  # type: ignore
            data["ai_client"] = dp.workflow_data.get("ai_client")

        return await handler(event, data)
