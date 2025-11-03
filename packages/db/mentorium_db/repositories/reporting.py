from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mentorium_core.schemas import ParentProfile, ProgressReport, ProgressTestScore
from mentorium_core.services.reporting import ReportRepository

from .. import models


class SqlReportRepository(ReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_parent_profile(self, chat_id: str) -> ParentProfile | None:
        stmt = select(models.ParentChat).where(models.ParentChat.id == chat_id)
        result = await self._session.scalar(stmt)
        if result is None or result.learner is None:
            return None

        return ParentProfile(
            parent_chat_id=result.id,
            parent_email=result.learner.parent_email,
            subscription_active=result.is_active,
            child_name=f"{result.learner.first_name} {result.learner.last_name}",
        )

    async def fetch_latest_tests(self, learner_id: str) -> list[ProgressTestScore]:
        stmt = (
            select(models.ProgressReport)
            .where(models.ProgressReport.learner_id == learner_id)
            .order_by(models.ProgressReport.created_at.desc())
            .limit(1)
        )
        report = await self._session.scalar(stmt)
        if report is None:
            return []

        payload: list[dict[str, Any]] = json.loads(report.tests_payload)
        return [ProgressTestScore(**item) for item in payload]

    async def register_generated_report(self, report: ProgressReport) -> None:
        payload = {
            "strengths": "\n".join(report.strengths),
            "focus_areas": "\n".join(report.focus_areas),
            "milestones": "\n".join(report.upcoming_milestones),
            "tests_payload": json.dumps([test.model_dump() for test in report.tests], ensure_ascii=False),
        }

        db_report = models.ProgressReport(
            id=report.generated_at.strftime("%Y%m%d%H%M%S"),
            learner_id=report.learner_id,
            reporting_period=report.reporting_period,
            strengths=payload["strengths"],
            focus_areas=payload["focus_areas"],
            milestones=payload["milestones"],
            tests_payload=payload["tests_payload"],
        )
        self._session.add(db_report)
