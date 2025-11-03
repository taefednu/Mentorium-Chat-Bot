"""
Structured logging с использованием structlog
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Добавить контекст приложения в лог"""
    # Добавляем app name если его нет
    if "app" not in event_dict:
        event_dict["app"] = "mentorium"
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_logs: bool = False,
    dev_mode: bool = False,
) -> None:
    """
    Настроить структурированное логирование
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        json_logs: Использовать JSON формат (для продакшена)
        dev_mode: Режим разработки (красивый вывод)
    """
    # Процессоры для всех логов
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # JSON формат для продакшена (легко парсится в ELK/Loki)
        renderer = structlog.processors.JSONRenderer()
    elif dev_mode:
        # Красивый цветной вывод для разработки
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )
    else:
        # Простой текстовый формат
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Настраиваем standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())

    # Уменьшаем verbosity сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Получить структурированный логгер
    
    Args:
        name: Имя логгера (обычно __name__)
        
    Returns:
        Структурированный логгер с bind() методом для добавления контекста
        
    Example:
        logger = get_logger(__name__)
        logger.info("user_registered", user_id=123, email="test@example.com")
        
        # С контекстом
        log = logger.bind(request_id="abc-123")
        log.info("processing_request")
    """
    return structlog.get_logger(name)
