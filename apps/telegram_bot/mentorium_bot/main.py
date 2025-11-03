from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .dependencies import create_ai_client, create_bot
from .handlers import dialog

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = create_bot()
    bot["ai_client"] = create_ai_client()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(dialog.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
