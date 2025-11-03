"""
Репозиторий для работы с родителями
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Parent, ParentStudent


class ParentRepository:
    """CRUD операции для родителей"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Parent | None:
        """Получить родителя по Telegram ID"""
        result = await self.session.execute(select(Parent).where(Parent.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, parent_id: int) -> Parent | None:
        """Получить родителя по ID"""
        result = await self.session.execute(select(Parent).where(Parent.id == parent_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        telegram_username: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        language_code: str = "ru",
    ) -> Parent:
        """Создать нового родителя"""
        parent = Parent(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            telegram_username=telegram_username,
            phone=phone,
            email=email,
            language_code=language_code,
        )
        self.session.add(parent)
        await self.session.flush()
        await self.session.refresh(parent)
        return parent

    async def update(self, parent: Parent, **kwargs) -> Parent:
        """Обновить данные родителя"""
        for key, value in kwargs.items():
            if hasattr(parent, key):
                setattr(parent, key, value)
        await self.session.flush()
        await self.session.refresh(parent)
        return parent

    async def deactivate(self, parent_id: int) -> bool:
        """Деактивировать родителя"""
        parent = await self.get_by_id(parent_id)
        if parent:
            parent.is_active = False
            await self.session.flush()
            return True
        return False

    async def get_all_active(self, limit: int = 100, offset: int = 0) -> list[Parent]:
        """Получить всех активных родителей (с пагинацией)"""
        result = await self.session.execute(
            select(Parent).where(Parent.is_active == True).limit(limit).offset(offset)  # noqa: E712
        )
        return list(result.scalars().all())

    async def add_student(self, parent_id: int, student_id: str) -> ParentStudent:
        """
        Привязать ученика к родителю
        
        Args:
            parent_id: ID родителя в Bot DB
            student_id: ID ученика в Platform DB
        """
        parent_student = ParentStudent(parent_id=parent_id, platform_student_id=student_id)
        self.session.add(parent_student)
        await self.session.flush()
        await self.session.refresh(parent_student)
        return parent_student

    async def remove_student(self, parent_id: int, student_id: str) -> bool:
        """Отвязать ученика от родителя"""
        result = await self.session.execute(
            select(ParentStudent).where(
                ParentStudent.parent_id == parent_id,
                ParentStudent.platform_student_id == student_id,
            )
        )
        parent_student = result.scalar_one_or_none()
        if parent_student:
            await self.session.delete(parent_student)
            await self.session.flush()
            return True
        return False

    async def get_students(self, parent_id: int) -> list[ParentStudent]:
        """Получить всех учеников родителя"""
        result = await self.session.execute(
            select(ParentStudent).where(ParentStudent.parent_id == parent_id)
        )
        return list(result.scalars().all())
