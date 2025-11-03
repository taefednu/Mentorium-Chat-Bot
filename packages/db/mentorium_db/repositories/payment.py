"""
Репозиторий для работы с платежами
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Payment


class PaymentRepository:
    """CRUD операции для платежей"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_transaction_id(self, transaction_id: str) -> Payment | None:
        """Получить платёж по ID транзакции"""
        result = await self.session.execute(
            select(Payment).where(Payment.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, payment_id: int) -> Payment | None:
        """Получить платёж по ID"""
        result = await self.session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        parent_id: int,
        transaction_id: str,
        provider: str,
        amount: Decimal,
        currency: str = "UZS",
        external_ref: str | None = None,
        payment_metadata: str | None = None,
    ) -> Payment:
        """Создать запись о платеже"""
        payment = Payment(
            parent_id=parent_id,
            transaction_id=transaction_id,
            provider=provider,
            amount=amount,
            currency=currency,
            external_ref=external_ref,
            payment_metadata=payment_metadata,
            status="PENDING",
        )
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)
        return payment

    async def mark_success(self, payment_id: int) -> Payment | None:
        """Пометить платёж как успешный"""
        payment = await self.get_by_id(payment_id)
        if payment:
            payment.status = "SUCCESS"
            payment.paid_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(payment)
        return payment

    async def mark_failed(self, payment_id: int) -> Payment | None:
        """Пометить платёж как неудачный"""
        payment = await self.get_by_id(payment_id)
        if payment:
            payment.status = "FAILED"
            payment.failed_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(payment)
        return payment

    async def mark_cancelled(self, payment_id: int) -> Payment | None:
        """Отменить платёж"""
        payment = await self.get_by_id(payment_id)
        if payment:
            payment.status = "CANCELLED"
            await self.session.flush()
            await self.session.refresh(payment)
        return payment

    async def get_parent_payments(
        self, parent_id: int, limit: int = 50, offset: int = 0
    ) -> list[Payment]:
        """Получить все платежи родителя"""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.parent_id == parent_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_successful_payments(
        self, parent_id: int, limit: int = 50, offset: int = 0
    ) -> list[Payment]:
        """Получить успешные платежи родителя"""
        result = await self.session.execute(
            select(Payment)
            .where(and_(Payment.parent_id == parent_id, Payment.status == "SUCCESS"))
            .order_by(Payment.paid_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_pending_payments(self, older_than_minutes: int = 15) -> list[Payment]:
        """Получить зависшие платежи (PENDING дольше N минут)"""
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        result = await self.session.execute(
            select(Payment).where(and_(Payment.status == "PENDING", Payment.created_at < threshold))
        )
        return list(result.scalars().all())
