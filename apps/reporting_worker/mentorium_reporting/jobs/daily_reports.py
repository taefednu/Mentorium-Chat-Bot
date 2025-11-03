from __future__ import annotations

import logging

from mentorium_ai_client import MentorPrompt, MentoriumAIClient
from mentorium_core.services.reporting import ParentReportBuilder
from mentorium_db import get_session
from mentorium_db.repositories import SqlReportRepository

logger = logging.getLogger(__name__)


async def run_daily_reports(ai_client: MentoriumAIClient) -> None:
    async with get_session() as session:
        repository = SqlReportRepository(session)
        builder = ParentReportBuilder(repository)

        # TODO: заменить на выборку реальных учеников из базы
        learners = ["demo-parent-chat"]
        for chat_id in learners:
            report = await builder.build(
                learner_id=chat_id,
                parent_chat_id=chat_id,
                period="текущую неделю",
            )
            logger.info("Report generated", extra={"summary": report.summary()})

            # Используем OpenAI для адаптации тона перед отправкой
            reply = await ai_client.generate_reply(
                MentorPrompt(prompt=report.summary()),
            )
            logger.info("Prepared AI message", extra={"message": reply})
