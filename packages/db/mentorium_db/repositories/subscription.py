"""
Репозиторий для управления подписками
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Subscription


class SubscriptionRepository:
    """CRUD операции для подписок"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_subscription(self, parent_id: int) -> Subscription | None:
        """Получить активную подписку родителя"""
        result = await self.session.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.parent_id == parent_id,
                    Subscription.status == "ACTIVE",
                    Subscription.expires_at > datetime.utcnow(),
                )
            )
            .order_by(Subscription.expires_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, subscription_id: int) -> Subscription | None:
        """Получить подписку по ID"""
        result = await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        parent_id: int,
        tariff: str,
        amount: Decimal,
        duration_days: int = 30,
        auto_renew: bool = False,
    ) -> Subscription:
        """Создать новую подписку"""
        starts_at = datetime.utcnow()
        expires_at = starts_at + timedelta(days=duration_days)

        subscription = Subscription(
            parent_id=parent_id,
            tariff=tariff,
            amount=amount,
            starts_at=starts_at,
            expires_at=expires_at,
            auto_renew=auto_renew,
            status="PENDING",
        )
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def activate(self, subscription_id: int) -> Subscription | None:
        """Активировать подписку"""
        subscription = await self.get_by_id(subscription_id)
        if subscription:
            subscription.status = "ACTIVE"
            await self.session.flush()
            await self.session.refresh(subscription)
        return subscription

    async def cancel(self, subscription_id: int) -> Subscription | None:
        """Отменить подписку"""
        subscription = await self.get_by_id(subscription_id)
        if subscription:
            subscription.status = "CANCELLED"
            subscription.cancelled_at = datetime.utcnow()
            subscription.auto_renew = False
            await self.session.flush()
            await self.session.refresh(subscription)
        return subscription

    async def expire(self, subscription_id: int) -> Subscription | None:
        """Пометить подписку как истёкшую"""
        subscription = await self.get_by_id(subscription_id)
        if subscription:
            subscription.status = "EXPIRED"
            await self.session.flush()
            await self.session.refresh(subscription)
        return subscription

    async def get_expiring_soon(self, days_threshold: int = 3) -> list[Subscription]:
        """Получить подписки, истекающие в ближайшие N дней"""
        threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
        result = await self.session.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == "ACTIVE",
                    Subscription.expires_at <= threshold_date,
                    Subscription.expires_at > datetime.utcnow(),
                )
            )
        )
        return list(result.scalars().all())

    async def get_expired(self) -> list[Subscription]:
        """Получить истёкшие подписки (статус ACTIVE, но уже прошла дата)"""
        result = await self.session.execute(
            select(Subscription).where(
                and_(Subscription.status == "ACTIVE", Subscription.expires_at <= datetime.utcnow())
            )
        )
        return list(result.scalars().all())

    async def has_active_subscription(self, parent_id: int) -> bool:
        """Проверить, есть ли активная подписка у родителя"""
        subscription = await self.get_active_subscription(parent_id)
        return subscription is not None
