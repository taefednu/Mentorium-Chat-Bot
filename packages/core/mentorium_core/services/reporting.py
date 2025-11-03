from __future__ import annotations

from typing import Protocol

from ..schemas import ParentProfile, ProgressReport, ProgressTestScore


class ReportRepository(Protocol):
    async def fetch_parent_profile(self, chat_id: str) -> ParentProfile | None: ...

    async def fetch_latest_tests(self, learner_id: str) -> list[ProgressTestScore]: ...

    async def register_generated_report(self, report: ProgressReport) -> None: ...


class ParentReportBuilder:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    async def build(self, learner_id: str, parent_chat_id: str, period: str) -> ProgressReport:
        parent = await self._repository.fetch_parent_profile(parent_chat_id)
        if parent is None:
            raise ValueError(f"Parent profile for chat_id={parent_chat_id} not found")

        tests = await self._repository.fetch_latest_tests(learner_id)

        report = ProgressReport(
            learner_id=learner_id,
            parent=parent,
            reporting_period=period,
            strengths=self._compose_strengths(tests),
            focus_areas=self._compose_focus(tests),
            upcoming_milestones=[
                "Практика с ChatGPT по теме недели",
                "Видео-урок по инструментам анализа данных",
            ],
            tests=tests,
        )

        await self._repository.register_generated_report(report)
        return report

    @staticmethod
    def _compose_strengths(test_results: list[ProgressTestScore]) -> list[str]:
        return [
            f"Успешно прошла контрольная '{result.title}' ({result.percentage:.0f}%)"
            for result in test_results
            if result.percentage >= 75
        ]

    @staticmethod
    def _compose_focus(test_results: list[ProgressTestScore]) -> list[str]:
        weakspots = [
            result for result in test_results if result.percentage < 60
        ]
        if not weakspots:
            return []

        return [
            f"Рекомендуем повторить тему '{result.title}' ("
            f"{result.percentage:.0f}% результатов)"
            for result in weakspots
        ]
