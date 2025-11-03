"""
Репозиторий для работы с историей отчётов
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ReportHistory


class ReportHistoryRepository:
    """CRUD операции для истории отчётов"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_report(
        self,
        parent_id: int,
        report_type: str,
        period_start: date,
        period_end: date,
        lessons_completed: int = 0,
        tests_taken: int = 0,
        average_score: float = 0.0,
        days_without_skip: int = 0,
        courses_in_progress: int = 0,
        courses_completed: int = 0,
        ai_recommendations: str | None = None,
    ) -> ReportHistory:
        """Создать запись об отправленном отчёте"""
        report = ReportHistory(
            parent_id=parent_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            lessons_completed=lessons_completed,
            tests_taken=tests_taken,
            average_score=average_score,
            days_without_skip=days_without_skip,
            courses_in_progress=courses_in_progress,
            courses_completed=courses_completed,
            ai_recommendations=ai_recommendations,
        )
        self.session.add(report)
        await self.session.flush()
        await self.session.refresh(report)
        return report

    async def get_last_report(
        self, parent_id: int, report_type: str | None = None
    ) -> ReportHistory | None:
        """
        Получить последний отправленный отчёт
        
        Args:
            parent_id: ID родителя
            report_type: Тип отчёта (weekly/monthly/on_demand), если None — любой тип
        """
        query = select(ReportHistory).where(ReportHistory.parent_id == parent_id)

        if report_type:
            query = query.where(ReportHistory.report_type == report_type)

        query = query.order_by(ReportHistory.sent_at.desc()).limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_reports_by_period(
        self, parent_id: int, start_date: date, end_date: date
    ) -> list[ReportHistory]:
        """Получить все отчёты за период"""
        result = await self.session.execute(
            select(ReportHistory)
            .where(
                and_(
                    ReportHistory.parent_id == parent_id,
                    ReportHistory.period_start >= start_date,
                    ReportHistory.period_end <= end_date,
                )
            )
            .order_by(ReportHistory.sent_at.desc())
        )
        return list(result.scalars().all())

    async def should_send_weekly_report(self, parent_id: int) -> bool:
        """
        Проверить, нужно ли отправлять еженедельный отчёт
        
        Отчёт отправляется, если последний weekly отчёт был >7 дней назад
        """
        last_report = await self.get_last_report(parent_id, report_type="weekly")

        if not last_report:
            return True  # Ещё не отправляли

        days_since_last = (datetime.utcnow().date() - last_report.period_end).days
        return days_since_last >= 7

    async def should_send_monthly_report(self, parent_id: int) -> bool:
        """
        Проверить, нужно ли отправлять месячный отчёт
        
        Отчёт отправляется раз в месяц
        """
        last_report = await self.get_last_report(parent_id, report_type="monthly")

        if not last_report:
            return True

        days_since_last = (datetime.utcnow().date() - last_report.period_end).days
        return days_since_last >= 28  # ~1 месяц

    async def get_report_stats(self, parent_id: int, days: int = 30) -> dict[str, float]:
        """
        Получить статистику по отчётам за последние N дней
        
        Returns:
            {"avg_lessons": 12.5, "avg_score": 87.3, "total_reports": 4}
        """
        since = datetime.utcnow().date() - timedelta(days=days)

        result = await self.session.execute(
            select(ReportHistory).where(
                and_(
                    ReportHistory.parent_id == parent_id,
                    ReportHistory.period_end >= since,
                )
            )
        )
        reports = list(result.scalars().all())

        if not reports:
            return {"avg_lessons": 0, "avg_score": 0, "total_reports": 0}

        avg_lessons = sum(r.lessons_completed for r in reports) / len(reports)
        avg_score = sum(float(r.average_score) for r in reports) / len(reports)

        return {
            "avg_lessons": round(avg_lessons, 1),
            "avg_score": round(avg_score, 1),
            "total_reports": len(reports),
        }

    async def delete_old_reports(self, days: int = 365) -> int:
        """
        Удалить старые отчёты (retention policy)
        
        Args:
            days: Удалить отчёты старше N дней
            
        Returns:
            Количество удалённых записей
        """
        threshold = datetime.utcnow().date() - timedelta(days=days)

        result = await self.session.execute(
            select(ReportHistory).where(ReportHistory.period_end < threshold)
        )
        reports = result.scalars().all()
        count = len(list(reports))

        for report in reports:
            await self.session.delete(report)

        await self.session.flush()
        return count
