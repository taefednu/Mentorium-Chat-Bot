"""
Health check endpoints для мониторинга
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from sqlalchemy import text

from mentorium_db.session import bot_session_factory, platform_session_factory

from .logging import get_logger

logger = get_logger(__name__)


async def check_database_health() -> dict[str, Any]:
    """
    Проверить подключение к базе данных бота
    
    Returns:
        Dict с информацией о статусе БД
    """
    start_time = time.time()
    try:
        async with bot_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()

        elapsed = time.time() - start_time

        return {
            "status": "healthy",
            "response_time_ms": round(elapsed * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("database_health_check_failed", error=str(e), exc_info=True)

        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round(elapsed * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def check_platform_database_health() -> dict[str, Any]:
    """
    Проверить подключение к базе данных платформы (read-only)
    
    Returns:
        Dict с информацией о статусе БД платформы
    """
    start_time = time.time()
    try:
        async with platform_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()

        elapsed = time.time() - start_time

        return {
            "status": "healthy",
            "response_time_ms": round(elapsed * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("platform_database_health_check_failed", error=str(e), exc_info=True)

        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round(elapsed * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def get_health_status() -> dict[str, Any]:
    """
    Полная проверка здоровья приложения
    
    Returns:
        Dict со статусом всех компонентов
    """
    db_health = await check_database_health()
    platform_db_health = await check_platform_database_health()

    # Общий статус
    overall_status = "healthy"
    if db_health["status"] == "unhealthy" or platform_db_health["status"] == "unhealthy":
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_health,
            "platform_database": platform_db_health,
        },
    }


async def get_readiness_status() -> dict[str, Any]:
    """
    Проверка готовности к приёму трафика (для Kubernetes readiness probe)
    
    Returns:
        Dict со статусом готовности
    """
    db_health = await check_database_health()

    # Для readiness достаточно проверить основную БД
    ready = db_health["status"] == "healthy"

    return {
        "ready": ready,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_health,
        },
    }


def get_liveness_status() -> dict[str, Any]:
    """
    Проверка живости приложения (для Kubernetes liveness probe)
    Простая проверка без внешних зависимостей
    
    Returns:
        Dict со статусом живости
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
