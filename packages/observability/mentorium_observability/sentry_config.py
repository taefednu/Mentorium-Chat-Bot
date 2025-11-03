"""
Sentry integration для отслеживания ошибок
"""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from .logging import get_logger

logger = get_logger(__name__)


def configure_sentry(
    dsn: str | None = None,
    environment: str = "development",
    release: str | None = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_tracing: bool = True,
) -> None:
    """
    Настроить Sentry для отслеживания ошибок
    
    Args:
        dsn: Sentry DSN (если None, Sentry не инициализируется)
        environment: Окружение (development, staging, production)
        release: Версия приложения (git commit sha или version)
        traces_sample_rate: Процент транзакций для трейсинга (0.0 - 1.0)
        profiles_sample_rate: Процент профилей для сбора (0.0 - 1.0)
        enable_tracing: Включить performance monitoring
    """
    if not dsn:
        logger.info("sentry_disabled", reason="no_dsn_provided")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        # Integrations
        integrations=[
            LoggingIntegration(
                level=None,  # Capture only errors by default
                event_level=None,  # Don't send logs as events
            ),
            AsyncioIntegration(),
            SqlalchemyIntegration(),
        ],
        # Performance Monitoring
        traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
        profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
        # Additional options
        send_default_pii=False,  # Don't send PII (email, username, etc)
        attach_stacktrace=True,
        before_send=before_send_filter,
    )

    logger.info(
        "sentry_configured",
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
    )


def before_send_filter(event, hint):
    """
    Фильтр событий перед отправкой в Sentry
    
    Можно использовать для:
    - Исключения определённых типов ошибок
    - Добавления дополнительного контекста
    - Скрытия чувствительных данных
    """
    # Игнорируем некоторые ошибки
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Игнорируем Telegram network errors (они временные)
        if exc_type.__name__ in ["NetworkError", "RetryAfter", "TimedOut"]:
            return None

        # Игнорируем cancelled tasks
        if exc_type.__name__ == "CancelledError":
            return None

    return event


def capture_exception(
    error: Exception,
    user_id: int | None = None,
    handler_name: str | None = None,
    extra: dict | None = None,
) -> None:
    """
    Отправить исключение в Sentry с контекстом
    
    Args:
        error: Исключение для отправки
        user_id: Telegram ID пользователя
        handler_name: Имя обработчика где произошла ошибка
        extra: Дополнительный контекст
    """
    with sentry_sdk.push_scope() as scope:
        # Добавляем пользователя
        if user_id:
            scope.set_user({"id": str(user_id)})

        # Добавляем контекст
        if handler_name:
            scope.set_tag("handler", handler_name)

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        # Отправляем
        sentry_sdk.capture_exception(error)

        logger.error(
            "exception_sent_to_sentry",
            error=str(error),
            user_id=user_id,
            handler=handler_name,
        )


def capture_message(
    message: str,
    level: str = "info",
    user_id: int | None = None,
    extra: dict | None = None,
) -> None:
    """
    Отправить сообщение в Sentry
    
    Args:
        message: Сообщение
        level: Уровень (info, warning, error, fatal)
        user_id: Telegram ID пользователя
        extra: Дополнительный контекст
    """
    # Convert string to valid Sentry level
    valid_levels = {"debug", "info", "warning", "error", "fatal", "critical"}
    sentry_level = level.lower() if level.lower() in valid_levels else "info"
    
    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": str(user_id)})

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_message(message, level=sentry_level)  # type: ignore
