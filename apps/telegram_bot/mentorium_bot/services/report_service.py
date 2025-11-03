"""
Сервис для формирования отчётов о прогрессе учеников
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from mentorium_db import get_platform_session, get_session
from mentorium_db.repositories import (
    ParentRepository,
    PlatformRepository,
    ReportHistoryRepository,
)

if TYPE_CHECKING:
    from mentorium_ai_client import MentoriumAIClient, StudentContext

logger = logging.getLogger(__name__)


class ReportService:
    """Сервис для создания текстовых отчётов о прогрессе"""

    def __init__(self, ai_client: MentoriumAIClient):
        self.ai_client = ai_client

    async def generate_weekly_report(self, parent_telegram_id: int) -> str | None:
        """
        Сгенерировать еженедельный отчёт
        
        Returns:
            Отформатированный текст отчёта или None если нет данных
        """
        # Определяем период (последние 7 дней)
        today = datetime.utcnow().date()
        period_start = today - timedelta(days=7)
        period_end = today

        # Получаем данные
        stats = await self._get_student_stats(parent_telegram_id, period_start, period_end)

        if not stats:
            return None

        # Формируем текст отчёта
        report = self._format_weekly_report(stats, period_start, period_end)

        # Генерируем AI рекомендации
        try:
            ai_recommendations = await self._generate_ai_recommendations(
                stats["context"], scenario="progress"
            )
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations: {e}")
            ai_recommendations = "Продолжайте в том же темпе! 👍"

        report += f"\n\n💡 Рекомендации:\n{ai_recommendations}"

        # Сохраняем в историю
        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if parent:
                report_repo = ReportHistoryRepository(session)
                await report_repo.create_report(
                    parent_id=parent.id,
                    report_type="weekly",
                    period_start=period_start,
                    period_end=period_end,
                    lessons_completed=stats["lessons_completed"],
                    tests_taken=stats["tests_taken"],
                    average_score=stats["average_score"],
                    days_without_skip=stats["days_without_skip"],
                    courses_in_progress=len(stats["courses"]),
                    ai_recommendations=ai_recommendations,
                )
                await session.commit()

        return report

    async def generate_monthly_report(
        self, parent_telegram_id: int, subscription_expires_in_days: int
    ) -> str | None:
        """
        Сгенерировать месячный отчёт с напоминанием о подписке
        
        Args:
            parent_telegram_id: Telegram ID родителя
            subscription_expires_in_days: Через сколько дней истекает подписка
        """
        # Период — последние 30 дней
        today = datetime.utcnow().date()
        period_start = today - timedelta(days=30)
        period_end = today

        stats = await self._get_student_stats(parent_telegram_id, period_start, period_end)

        if not stats:
            return None

        # Формируем отчёт
        report = self._format_monthly_report(stats, period_start, period_end)

        # Добавляем напоминание о подписке
        report += f"\n\n💳 Подписка заканчивается через {subscription_expires_in_days} дня\n"
        report += "Не забудьте продлить, чтобы продолжить обучение!"

        # AI рекомендации
        try:
            ai_recommendations = await self._generate_ai_recommendations(
                stats["context"], scenario="recommendations"
            )
            report += f"\n\n💡 Итоги месяца:\n{ai_recommendations}"
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations: {e}")

        # Сохраняем
        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if parent:
                report_repo = ReportHistoryRepository(session)
                await report_repo.create_report(
                    parent_id=parent.id,
                    report_type="monthly",
                    period_start=period_start,
                    period_end=period_end,
                    lessons_completed=stats["lessons_completed"],
                    tests_taken=stats["tests_taken"],
                    average_score=stats["average_score"],
                    days_without_skip=stats["days_without_skip"],
                    courses_in_progress=len(stats["courses"]),
                    courses_completed=stats.get("courses_completed", 0),
                    ai_recommendations=ai_recommendations if "ai_recommendations" in locals() else None,
                )
                await session.commit()

        return report

    async def generate_on_demand_report(self, parent_telegram_id: int) -> str | None:
        """Сгенерировать отчёт по запросу (последние 7 дней)"""
        today = datetime.utcnow().date()
        period_start = today - timedelta(days=7)
        period_end = today

        stats = await self._get_student_stats(parent_telegram_id, period_start, period_end)

        if not stats:
            return "❌ Нет данных за последнюю неделю"

        report = f"📊 Текущий прогресс {stats['student_name']}\n\n"

        # Активные курсы
        if stats["courses"]:
            report += "📚 Активные курсы:\n"
            for course in stats["courses"][:3]:
                progress = course["progress"]
                report += f"• {course['name']}: {progress}% "
                # Примерная оценка времени до завершения
                if progress > 0 and progress < 100:
                    weeks_left = int((100 - progress) / (progress / 7))  # Грубая оценка
                    report += f"(~{weeks_left} нед.)"
                elif progress == 100:
                    report += "✅"
                report += "\n"

        # Последние тесты
        if stats["tests"]:
            report += f"\n📝 Последние тесты:\n"
            for test in stats["tests"][:3]:
                emoji = "⭐" if test["score"] >= 90 else "✅" if test["passed"] else "❌"
                days_ago = (today - test.get("date", today)).days if "date" in test else 0
                time_str = "сегодня" if days_ago == 0 else f"{days_ago} дн. назад"
                report += f"• {test['name']}: {test['score']}% {emoji} ({time_str})\n"

        # Активность
        report += f"\n✅ Активность:\n"
        report += f"• Дни без пропусков: 🔥 {stats['days_without_skip']} дней\n"
        report += f"• Последний визит: {stats.get('last_activity', 'сегодня')}\n"

        return report

    async def _get_student_stats(
        self, parent_telegram_id: int, period_start: date, period_end: date
    ) -> dict | None:
        """
        Получить статистику ученика за период из Platform DB
        
        Returns:
            Dict с метриками или None если ученик не найден
        """
        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if not parent:
                return None

            students = await parent_repo.get_students(parent.id)
            if not students:
                return None

            student_id = students[0].platform_student_id

        # Получаем данные из Platform DB
        async with get_platform_session() as platform_session:
            platform_repo = PlatformRepository(platform_session)
            student = await platform_repo.get_student_by_id(student_id)

            if not student:
                return None

            courses = await platform_repo.get_student_course_progress(student_id)
            tests = await platform_repo.get_student_test_results(student_id, limit=10)
            days_active = await platform_repo.get_student_activity_days(
                student_id, days=(period_end - period_start).days
            )

            # Фильтруем тесты за период (если есть дата)
            # tests_in_period = [t for t in tests if period_start <= t.completed_at.date() <= period_end]

            # Считаем метрики
            lessons_completed = sum(c.lessons_completed for c in courses)
            tests_taken = len(tests)  # Упрощённо — берём все последние
            average_score = (
                sum(t.score for t in tests) / len(tests) if tests else 0.0
            )

            # Формируем StudentContext для AI
            from mentorium_ai_client import StudentContext

            context = StudentContext(
                student_name=student.first_name,
                age=student.age,
                courses=[
                    {
                        "name": c.course_name,
                        "progress": c.progress_percent,
                        "lessons_completed": c.lessons_completed,
                    }
                    for c in courses
                ],
                recent_tests=[
                    {"name": t.test_name, "score": t.score, "passed": t.passed}
                    for t in tests[:5]
                ],
                activity_days=days_active,
                last_activity=None,
            )

            return {
                "student_name": student.first_name,
                "lessons_completed": lessons_completed,
                "tests_taken": tests_taken,
                "average_score": average_score,
                "days_without_skip": days_active,
                "courses": [
                    {
                        "name": c.course_name,
                        "progress": c.progress_percent,
                        "lessons_completed": c.lessons_completed,
                    }
                    for c in courses
                ],
                "tests": [
                    {
                        "name": t.test_name,
                        "score": t.score,
                        "passed": t.passed,
                        "date": t.completed_at.date(),
                    }
                    for t in tests
                ],
                "context": context,
            }

    def _format_weekly_report(
        self, stats: dict, period_start: date, period_end: date
    ) -> str:
        """Форматирование еженедельного отчёта"""
        start_str = period_start.strftime("%d %b")
        end_str = period_end.strftime("%d %b")

        report = f"📅 Недельный отчёт ({start_str} - {end_str})\n\n"
        report += f"👤 Ученик: {stats['student_name']}\n\n"

        report += "✅ Активность:\n"
        report += f"• Уроков завершено: {stats['lessons_completed']}\n"
        report += f"• Дни без пропусков: 🔥 {stats['days_without_skip']} дней\n"

        if stats["tests"]:
            report += f"\n📝 Тесты за неделю ({stats['tests_taken']} шт):\n"
            for test in stats["tests"][:3]:
                emoji = "⭐" if test["score"] >= 90 else "✅" if test["passed"] else "❌"
                report += f"• {test['name']}: {test['score']:.0f}% {emoji}\n"

        if stats["courses"]:
            report += f"\n📚 Прогресс по курсам:\n"
            for course in stats["courses"]:
                progress = course["progress"]
                emoji = "✅ Завершён!" if progress >= 100 else ""
                report += f"• {course['name']}: {progress:.0f}% {emoji}\n"

        return report

    def _format_monthly_report(
        self, stats: dict, period_start: date, period_end: date
    ) -> str:
        """Форматирование месячного отчёта"""
        start_str = period_start.strftime("%d %b")
        end_str = period_end.strftime("%d %b")

        report = f"📊 Месячный отчёт ({start_str} - {end_str})\n\n"
        report += f"👤 {stats['student_name']}\n\n"

        report += "📈 За месяц:\n"
        report += f"• Уроков пройдено: {stats['lessons_completed']}\n"
        report += f"• Тестов сдано: {stats['tests_taken']} "
        if stats["tests_taken"] > 0:
            report += f"(средний балл: {stats['average_score']:.0f}%)\n"
        else:
            report += "\n"

        total_days = (period_end - period_start).days
        report += f"• Дни без пропусков: 🔥 {stats['days_without_skip']} из {total_days}\n"

        # Завершённые курсы
        completed_courses = [c for c in stats["courses"] if c["progress"] >= 100]
        if completed_courses:
            report += f"• Курсов завершено: {len(completed_courses)}\n\n"
            report += "🎯 Достижения:\n"
            for course in completed_courses:
                report += f"✅ {course['name']} — сертификат получен\n"

        return report

    async def _generate_ai_recommendations(
        self, context: StudentContext, scenario: str
    ) -> str:
        """Сгенерировать AI рекомендации на основе контекста"""
        from mentorium_ai_client import MentorPrompt

        prompt = MentorPrompt(
            prompt=(
                "Дай краткие рекомендации родителю (2-3 совета) на основе прогресса ребёнка. "
                "Будь позитивным, конкретным и мотивирующим."
            )
        )

        reply = await self.ai_client.generate_reply(
            prompt, student_context=context, scenario=scenario
        )

        return reply
