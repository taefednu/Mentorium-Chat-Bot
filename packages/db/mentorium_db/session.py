from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .settings import DatabaseSettings

_settings = DatabaseSettings()

# Bot DB (read-write) — основная БД бота
_bot_engine = create_async_engine(_settings.async_url, echo=False, future=True, pool_pre_ping=True)
bot_session_factory = async_sessionmaker(_bot_engine, expire_on_commit=False, class_=AsyncSession)

# Platform DB (read-only) — БД платформы Mentorium
_platform_engine = create_async_engine(
    _settings.platform_async_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    # Read-only настройки
    connect_args={"server_settings": {"default_transaction_read_only": "on"}},
)
platform_session_factory = async_sessionmaker(
    _platform_engine, expire_on_commit=False, class_=AsyncSession
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Получить сессию для Bot DB (read-write)
    
    Используется для работы с данными бота: родители, подписки, диалоги и т.д.
    """
    session = bot_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_platform_session() -> AsyncIterator[AsyncSession]:
    """
    Получить read-only сессию для Platform DB
    
    Используется для чтения данных учеников из платформы Mentorium.
    """
    session = platform_session_factory()
    try:
        yield session
        # Для read-only не нужен commit
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
