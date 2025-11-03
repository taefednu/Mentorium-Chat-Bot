"""
Event logging service для трекинга действий пользователей
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mentorium_db.models import EventLog
from mentorium_db.session import bot_session_factory

from .logging import get_logger

logger = get_logger(__name__)


class EventLogService:
    """
    Сервис для логирования событий в БД
    
    События:
    - USER_ACTION: действия пользователя (регистрация, диалог, отчёт)
    - PAYMENT: платежи и подписки
    - ERROR: ошибки и исключения
    - SYSTEM: системные события (запуск, остановка)
    """

    EVENT_TYPES = {
        "USER_ACTION": ["registration", "dialog", "report_request", "subscription"],
        "PAYMENT": ["payment_created", "payment_success", "payment_failed", "subscription_activated"],
        "ERROR": ["dialog_error", "payment_error", "api_error", "database_error"],
        "SYSTEM": ["bot_started", "bot_stopped", "migration_applied", "scheduled_task"],
    }

    @staticmethod
    async def log_event(
        event_type: str,
        event_name: str,
        user_telegram_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        severity: str = "INFO",
    ) -> None:
        """
        Записать событие в БД
        
        Args:
            event_type: Тип события (USER_ACTION, PAYMENT, ERROR, SYSTEM)
            event_name: Название события (registration, payment_success, etc)
            user_telegram_id: Telegram ID пользователя (опционально)
            metadata: Дополнительные данные события (JSON)
            severity: Уровень важности (INFO, WARNING, ERROR)
        """
        try:
            async with bot_session_factory() as session:
                event = EventLog(
                    event_type=event_type,
                    event_name=event_name,
                    user_telegram_id=user_telegram_id,
                    metadata=json.dumps(metadata) if metadata else None,
                    severity=severity,
                    created_at=datetime.utcnow(),
                )
                session.add(event)
                await session.commit()

                logger.info(
                    "event_logged",
                    event_type=event_type,
                    event_name=event_name,
                    user_id=user_telegram_id,
                    severity=severity,
                )
        except Exception as e:
            # Не падаем если логирование не сработало
            logger.error(
                "event_log_failed",
                error=str(e),
                event_type=event_type,
                event_name=event_name,
                exc_info=True,
            )

    @staticmethod
    async def log_user_action(
        action: str,
        user_telegram_id: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Логировать действие пользователя"""
        await EventLogService.log_event(
            event_type="USER_ACTION",
            event_name=action,
            user_telegram_id=user_telegram_id,
            metadata=metadata,
            severity="INFO",
        )

    @staticmethod
    async def log_payment(
        payment_event: str,
        user_telegram_id: int,
        amount: float | None = None,
        provider: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Логировать платёжное событие"""
        payment_metadata = metadata or {}
        if amount:
            payment_metadata["amount"] = amount
        if provider:
            payment_metadata["provider"] = provider

        severity = "ERROR" if "failed" in payment_event else "INFO"

        await EventLogService.log_event(
            event_type="PAYMENT",
            event_name=payment_event,
            user_telegram_id=user_telegram_id,
            metadata=payment_metadata,
            severity=severity,
        )

    @staticmethod
    async def log_error(
        error_name: str,
        error_message: str,
        user_telegram_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Логировать ошибку"""
        error_metadata = metadata or {}
        error_metadata["error_message"] = error_message

        await EventLogService.log_event(
            event_type="ERROR",
            event_name=error_name,
            user_telegram_id=user_telegram_id,
            metadata=error_metadata,
            severity="ERROR",
        )

    @staticmethod
    async def log_system(
        system_event: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Логировать системное событие"""
        await EventLogService.log_event(
            event_type="SYSTEM",
            event_name=system_event,
            metadata=metadata,
            severity="INFO",
        )

    @staticmethod
    async def get_user_events(
        user_telegram_id: int,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[EventLog]:
        """
        Получить события пользователя
        
        Args:
            user_telegram_id: Telegram ID пользователя
            event_type: Фильтр по типу события
            limit: Максимальное количество событий
            
        Returns:
            Список событий
        """
        async with bot_session_factory() as session:
            query = select(EventLog).filter(EventLog.user_telegram_id == user_telegram_id)

            if event_type:
                query = query.filter(EventLog.event_type == event_type)

            query = query.order_by(EventLog.created_at.desc()).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())
