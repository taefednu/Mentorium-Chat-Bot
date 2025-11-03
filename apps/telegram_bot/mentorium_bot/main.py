from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .dependencies import create_ai_client, create_bot
from .handlers import dialog
from .handlers.registration import registration_router

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = create_bot()
    ai_client = create_ai_client()

    dp = Dispatcher(storage=MemoryStorage())
    
    # Добавляем ai_client в workflow_data для доступа из handlers
    dp.workflow_data.update(ai_client=ai_client)
    
    # Порядок важен: registration должен быть первым (обрабатывает /start)
    dp.include_router(registration_router)
    dp.include_router(dialog.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
