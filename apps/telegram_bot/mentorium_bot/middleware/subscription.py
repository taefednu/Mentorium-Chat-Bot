"""
Middleware для проверки активной подписки
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from mentorium_bot.services.billing_service import BillingService

logger = logging.getLogger(__name__)


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware для проверки активной подписки родителя
    
    Пропускает:
    - Команду /start (регистрация)
    - Команду /subscribe (оформление подписки)
    - Пользователей в grace period (3 дня после истечения)
    
    Блокирует:
    - Пользователей без активной подписки (после grace period)
    """

    # Команды, которые доступны без подписки
    ALLOWED_COMMANDS = ["/start", "/subscribe", "/help"]

    def __init__(self, billing_service: BillingService):
        super().__init__()
        self.billing_service = billing_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        # Проверяем, что это сообщение
        if not isinstance(event, Message):
            return await handler(event, data)

        # Проверяем, что есть from_user
        if not event.from_user:
            return await handler(event, data)

        # Проверяем, является ли это разрешённой командой
        if event.text and any(event.text.startswith(cmd) for cmd in self.ALLOWED_COMMANDS):
            return await handler(event, data)

        telegram_id = event.from_user.id

        # Проверяем наличие активной подписки
        has_subscription = await self.billing_service.has_active_subscription(telegram_id)

        if has_subscription:
            # Подписка активна — пропускаем
            return await handler(event, data)

        # Проверяем grace period
        in_grace_period = await self.billing_service.get_subscription_grace_period(telegram_id)

        if in_grace_period:
            # В grace period — пропускаем с предупреждением
            logger.info(f"User {telegram_id} is in grace period")
            return await handler(event, data)

        # Подписка истекла — блокируем
        logger.warning(f"User {telegram_id} has no active subscription")

        await event.answer(
            "❌ Ваша подписка истекла\n\n"
            "Для продолжения использования бота необходимо оформить подписку.\n\n"
            "Команда: /subscribe"
        )

        return None  # Блокируем обработку

    @staticmethod
    def should_check_subscription(event: Message) -> bool:
        """Проверить, нужно ли проверять подписку для этого сообщения"""
        # Не проверяем для callback_query, inline_query и т.д.
        return isinstance(event, Message) and event.from_user is not None
