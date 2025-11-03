"""
Репозиторий для работы с историей диалогов
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DialogMessage


class DialogRepository:
    """CRUD операции для истории диалогов"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(
        self,
        parent_id: int,
        role: str,
        content: str,
        tokens_used: int | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> DialogMessage:
        """Добавить сообщение в историю диалога"""
        message = DialogMessage(
            parent_id=parent_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            model=model,
            prompt_version=prompt_version,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_recent_history(
        self, parent_id: int, limit: int = 10, hours: int = 24
    ) -> list[DialogMessage]:
        """
        Получить недавнюю историю диалога для контекста AI
        
        Args:
            parent_id: ID родителя
            limit: Максимальное количество сообщений
            hours: Получить сообщения за последние N часов
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await self.session.execute(
            select(DialogMessage)
            .where(and_(DialogMessage.parent_id == parent_id, DialogMessage.timestamp >= since))
            .order_by(DialogMessage.timestamp.desc())
            .limit(limit)
        )
        # Возвращаем в хронологическом порядке (старые → новые)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def get_all_parent_messages(
        self, parent_id: int, limit: int = 100, offset: int = 0
    ) -> list[DialogMessage]:
        """Получить все сообщения родителя (для аналитики)"""
        result = await self.session.execute(
            select(DialogMessage)
            .where(DialogMessage.parent_id == parent_id)
            .order_by(DialogMessage.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete_old_messages(self, days: int = 180) -> int:
        """
        Удалить старые сообщения (retention policy)
        
        Args:
            days: Удалить сообщения старше N дней
            
        Returns:
            Количество удалённых записей
        """
        threshold = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(DialogMessage).where(DialogMessage.timestamp < threshold)
        )
        messages = result.scalars().all()
        count = len(list(messages))

        for message in messages:
            await self.session.delete(message)

        await self.session.flush()
        return count

    async def get_token_usage(
        self, parent_id: int, since: datetime | None = None
    ) -> dict[str, int]:
        """
        Получить статистику использования токенов
        
        Returns:
            {"total_tokens": 1234, "message_count": 56}
        """
        query = select(DialogMessage).where(DialogMessage.parent_id == parent_id)
        if since:
            query = query.where(DialogMessage.timestamp >= since)

        result = await self.session.execute(query)
        messages = result.scalars().all()

        total_tokens = sum(m.tokens_used or 0 for m in messages)
        message_count = len(list(messages))

        return {"total_tokens": total_tokens, "message_count": message_count}
