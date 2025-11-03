from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from mentorium_ai_client import MentoriumAIClient

from .config import ReportingSettings
from .jobs.daily_reports import run_daily_reports

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    settings = ReportingSettings()
    ai_client = MentoriumAIClient(settings.openai_api_key.get_secret_value())

    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_daily_reports,
        trigger=CronTrigger.from_crontab(settings.schedule_cron),
        kwargs={"ai_client": ai_client},
        id="daily-reports",
        replace_existing=True,
    )

    scheduler.start()
    logging.info("Reporting scheduler started")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logging.info("Scheduler stopping...")
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
