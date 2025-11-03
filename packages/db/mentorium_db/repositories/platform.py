"""
Репозиторий для чтения данных из Platform DB (read-only)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PlatformStudent:
    """
    Данные ученика из платформы Mentorium
    
    Это упрощённая модель для чтения основной информации.
    Полная схема platform DB находится в отдельной БД.
    """

    id: str
    first_name: str
    last_name: str
    email: str
    parent_email: str | None
    age: int | None
    created_at: datetime


@dataclass
class CourseProgress:
    """Прогресс ученика по курсу"""

    student_id: str
    course_id: str
    course_name: str
    progress_percent: float
    lessons_completed: int
    lessons_total: int
    last_activity: datetime | None


@dataclass
class TestResult:
    """Результат теста ученика"""

    student_id: str
    test_id: str
    test_name: str
    score: float
    max_score: float
    passed: bool
    completed_at: datetime


class PlatformRepository:
    """
    Репозиторий для read-only доступа к Platform DB
    
    Используется для получения данных учеников, курсов, тестов из основной БД платформы.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_student_by_id(self, student_id: str) -> PlatformStudent | None:
        """
        Получить ученика по ID
        
        ВАЖНО: Пока у нас нет доступа к platform DB, используем заглушку.
        После получения credentials нужно будет переписать на реальные запросы.
        """
        # TODO: Реализовать реальный запрос к platform DB
        # query = select(PlatformStudentModel).where(PlatformStudentModel.id == student_id)
        # result = await self.session.execute(query)
        # return result.scalar_one_or_none()

        # Временная заглушка (mock data)
        return None

    async def get_student_by_email(self, email: str) -> PlatformStudent | None:
        """
        Получить ученика по email
        
        Используется при регистрации родителя для привязки к ребёнку.
        """
        # TODO: Реализовать реальный запрос
        return None

    async def get_student_by_parent_email(self, parent_email: str) -> list[PlatformStudent]:
        """
        Получить всех учеников родителя по email
        
        Один родитель может иметь несколько детей на платформе.
        """
        # TODO: Реализовать реальный запрос
        return []

    async def get_student_course_progress(self, student_id: str) -> list[CourseProgress]:
        """
        Получить прогресс ученика по всем курсам
        
        Используется для формирования отчётов и контекста AI.
        """
        # TODO: Реализовать реальный запрос
        return []

    async def get_student_test_results(
        self, student_id: str, limit: int = 10
    ) -> list[TestResult]:
        """
        Получить последние результаты тестов ученика
        
        Args:
            student_id: ID ученика
            limit: Количество последних результатов
            
        Returns:
            Список результатов тестов, отсортированных по дате (новые первые)
        """
        # TODO: Реализовать реальный запрос
        return []

    async def check_connection(self) -> bool:
        """
        Проверить подключение к Platform DB
        
        Полезно для диагностики и healthcheck.
        """
        try:
            result = await self.session.execute(text("SELECT 1"))
            result.scalar()
            return True
        except Exception:
            return False

    async def get_student_activity_days(self, student_id: str, days: int = 30) -> int:
        """
        Получить количество дней активности ученика за последний период
        
        Используется для streak и мотивационных уведомлений.
        """
        # TODO: Реализовать реальный запрос
        return 0

    async def validate_student_code(self, code: str) -> PlatformStudent | None:
        """
        Валидировать код привязки ученика
        
        При регистрации родитель может ввести специальный код вместо email.
        Код генерируется платформой для упрощения процесса.
        
        Args:
            code: Код привязки (например, "ABC123")
            
        Returns:
            Данные ученика если код валиден, иначе None
        """
        # TODO: Реализовать реальный запрос
        # query = select(PlatformStudentModel).where(PlatformStudentModel.link_code == code)
        # result = await self.session.execute(query)
        # return result.scalar_one_or_none()
        return None
