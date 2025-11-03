"""
Репозиторий для работы с уведомлениями
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Notification


class NotificationRepository:
    """CRUD операции для уведомлений"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        parent_id: int,
        notification_type: str,
        message: str,
        title: str | None = None,
    ) -> Notification:
        """Создать уведомление"""
        notification = Notification(
            parent_id=parent_id,
            notification_type=notification_type,
            title=title,
            message=message,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def mark_sent(self, notification_id: int) -> Notification | None:
        """Пометить уведомление как отправленное"""
        notification = await self.get_by_id(notification_id)
        if notification:
            notification.sent_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(notification)
        return notification

    async def mark_read(self, notification_id: int) -> Notification | None:
        """Пометить уведомление как прочитанное"""
        notification = await self.get_by_id(notification_id)
        if notification:
            notification.read_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: int) -> Notification | None:
        """Получить уведомление по ID"""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_pending(self, limit: int = 100) -> list[Notification]:
        """Получить неотправленные уведомления"""
        result = await self.session.execute(
            select(Notification)
            .where(Notification.sent_at.is_(None))
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_parent_unread(self, parent_id: int) -> list[Notification]:
        """Получить непрочитанные уведомления родителя"""
        result = await self.session.execute(
            select(Notification)
            .where(
                and_(
                    Notification.parent_id == parent_id,
                    Notification.sent_at.isnot(None),
                    Notification.read_at.is_(None),
                )
            )
            .order_by(Notification.sent_at.desc())
        )
        return list(result.scalars().all())

    async def get_parent_notifications(
        self, parent_id: int, limit: int = 50, offset: int = 0
    ) -> list[Notification]:
        """Получить все уведомления родителя"""
        result = await self.session.execute(
            select(Notification)
            .where(Notification.parent_id == parent_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_today_notifications(self, parent_id: int) -> int:
        """Посчитать количество уведомлений за сегодня (для rate limiting)"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(Notification).where(
                and_(
                    Notification.parent_id == parent_id,
                    Notification.sent_at >= today_start,
                    Notification.sent_at.isnot(None),
                )
            )
        )
        return len(list(result.scalars().all()))

    async def delete_old_notifications(self, days: int = 90) -> int:
        """Удалить старые уведомления"""
        threshold = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(Notification).where(Notification.created_at < threshold)
        )
        notifications = result.scalars().all()
        count = len(list(notifications))

        for notification in notifications:
            await self.session.delete(notification)

        await self.session.flush()
        return count
