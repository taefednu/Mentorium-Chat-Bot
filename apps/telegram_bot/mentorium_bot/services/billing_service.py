"""
Сервис для управления подписками и платежами
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from mentorium_db import get_session
from mentorium_db.repositories import ParentRepository, PaymentRepository, SubscriptionRepository

from .payment import ClickProvider, PayMeProvider

if TYPE_CHECKING:
    from mentorium_bot.config import BotSettings

logger = logging.getLogger(__name__)


class BillingService:
    """Сервис для работы с подписками и платежами"""

    # Тарифы (ключ -> (дней, цена в UZS))
    TARIFFS = {
        "monthly": (30, 99000),  # 99,000 UZS ~9 USD
        "quarterly": (90, 249000),  # 249,000 UZS ~23 USD
        "annual": (365, 899000),  # 899,000 UZS ~82 USD
    }

    def __init__(self, settings: BotSettings):
        self.settings = settings

        # Инициализируем платёжные провайдеры
        self.payme = PayMeProvider(
            merchant_id=settings.payme_merchant_id,
            secret_key=settings.payme_secret_key.get_secret_value() if settings.payme_secret_key else None,
            test_mode=settings.payme_test_mode,
        )

        self.click = ClickProvider(
            merchant_id=settings.click_merchant_id,
            service_id=settings.click_service_id,
            secret_key=settings.click_secret_key.get_secret_value() if settings.click_secret_key else None,
            test_mode=settings.click_test_mode,
        )

    def get_available_providers(self) -> list[str]:
        """Получить список доступных платёжных провайдеров"""
        providers = []
        if self.payme.is_available():
            providers.append("payme")
        if self.click.is_available():
            providers.append("click")
        providers.append("telegram_stars")  # Всегда доступен
        return providers

    async def create_subscription(
        self,
        parent_telegram_id: int,
        tariff: str,
        payment_provider: str,
    ) -> tuple[str | None, Decimal]:
        """
        Создать подписку и сгенерировать ссылку на оплату
        
        Args:
            parent_telegram_id: Telegram ID родителя
            tariff: monthly | quarterly | annual
            payment_provider: payme | click | telegram_stars
            
        Returns:
            (payment_url, amount) или (None, amount) если провайдер недоступен
        """
        if tariff not in self.TARIFFS:
            raise ValueError(f"Unknown tariff: {tariff}")

        days, amount_uzs = self.TARIFFS[tariff]
        amount = Decimal(amount_uzs)

        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if not parent:
                raise ValueError(f"Parent {parent_telegram_id} not found")

            # Создаём подписку
            subscription_repo = SubscriptionRepository(session)
            subscription = await subscription_repo.create(
                parent_id=parent.id,
                tariff=tariff,
                amount=amount,
                duration_days=days,
                auto_renew=False,
            )

            # Создаём платёж
            payment_repo = PaymentRepository(session)
            payment = await payment_repo.create(
                parent_id=parent.id,
                subscription_id=subscription.id,
                transaction_id=f"sub_{subscription.id}_{int(datetime.utcnow().timestamp())}",
                amount=amount,
                currency="UZS",
                provider=payment_provider.upper(),
            )

            await session.commit()

            # Генерируем ссылку на оплату
            payment_url = None

            if payment_provider == "payme" and self.payme.is_available():
                payment_url = self.payme.create_payment_link(
                    amount=amount,
                    order_id=str(payment.id),
                    return_url=f"https://t.me/your_bot?start=payment_{payment.id}",
                )
            elif payment_provider == "click" and self.click.is_available():
                payment_url = self.click.create_payment_link(
                    amount=amount,
                    order_id=str(payment.id),
                    return_url=f"https://t.me/your_bot?start=payment_{payment.id}",
                )
            elif payment_provider == "telegram_stars":
                # Telegram Stars обрабатывается отдельно через InvoiceHandler
                payment_url = None
            else:
                logger.warning(f"Payment provider {payment_provider} not available")

            logger.info(
                f"Created subscription {subscription.id} for parent {parent.id}, "
                f"tariff={tariff}, provider={payment_provider}"
            )

            return payment_url, amount

    async def activate_subscription(
        self,
        payment_id: int,
        external_transaction_id: str | None = None,
    ) -> bool:
        """
        Активировать подписку после успешного платежа
        
        Args:
            payment_id: ID платежа в нашей БД
            external_transaction_id: ID транзакции в платёжной системе
            
        Returns:
            True если активация успешна
        """
        async with get_session() as session:
            payment_repo = PaymentRepository(session)
            payment = await payment_repo.get_by_id(payment_id)

            if not payment:
                logger.error(f"Payment {payment_id} not found")
                return False

            if payment.status == "SUCCESS":
                logger.warning(f"Payment {payment_id} already paid")
                return True

            # Обновляем платёж
            await payment_repo.mark_success(payment_id=payment_id)

            # Обновляем external_ref если передан
            if external_transaction_id:
                payment.external_ref = external_transaction_id

            # Активируем подписку
            if payment.subscription_id:
                subscription_repo = SubscriptionRepository(session)
                await subscription_repo.activate(payment.subscription_id)
            else:
                logger.error(f"Payment {payment_id} has no subscription_id")
                return False

            await session.commit()

            logger.info(f"Activated subscription for payment {payment_id}")
            return True

    async def cancel_subscription(self, parent_telegram_id: int) -> bool:
        """Отменить активную подписку родителя"""
        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if not parent:
                return False

            subscription_repo = SubscriptionRepository(session)
            subscription = await subscription_repo.get_active_subscription(parent.id)

            if not subscription:
                logger.warning(f"No active subscription for parent {parent.id}")
                return False

            await subscription_repo.cancel(subscription.id)
            await session.commit()

            logger.info(f"Cancelled subscription {subscription.id} for parent {parent.id}")
            return True

    async def check_subscription_status(self, parent_telegram_id: int) -> dict | None:
        """
        Проверить статус подписки родителя
        
        Returns:
            {"active": bool, "expires_at": datetime, "days_left": int, "tariff": str}
        """
        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if not parent:
                return None

            subscription_repo = SubscriptionRepository(session)
            subscription = await subscription_repo.get_active_subscription(parent.id)

            if not subscription:
                return {"active": False, "expires_at": None, "days_left": 0, "tariff": None}

            days_left = (subscription.expires_at - datetime.utcnow()).days

            return {
                "active": True,
                "expires_at": subscription.expires_at,
                "days_left": max(0, days_left),
                "tariff": subscription.tariff,
                "auto_renew": subscription.auto_renew,
            }

    async def has_active_subscription(self, parent_telegram_id: int) -> bool:
        """Проверить, есть ли активная подписка у родителя"""
        status = await self.check_subscription_status(parent_telegram_id)
        return status is not None and status["active"]

    async def get_subscription_grace_period(self, parent_telegram_id: int) -> bool:
        """
        Проверить, находится ли родитель в grace period (3 дня после истечения)
        
        Returns:
            True если в grace period, False если подписка активна или истекла >3 дней назад
        """
        async with get_session() as session:
            parent_repo = ParentRepository(session)
            parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

            if not parent:
                return False

            subscription_repo = SubscriptionRepository(session)
            subscription = await subscription_repo.get_active_subscription(parent.id)

            if not subscription:
                return False

            # Проверяем, истекла ли подписка
            if subscription.expires_at > datetime.utcnow():
                return False  # Ещё активна

            # Проверяем, прошло ли меньше 3 дней
            days_expired = (datetime.utcnow() - subscription.expires_at).days
            return 0 < days_expired <= 3

    async def expire_old_subscriptions(self) -> int:
        """
        Пометить истёкшие подписки как EXPIRED
        
        Вызывается по расписанию (раз в день)
        
        Returns:
            Количество истёкших подписок
        """
        count = 0

        async with get_session() as session:
            subscription_repo = SubscriptionRepository(session)
            expired_subs = await subscription_repo.get_expired()

            for sub in expired_subs:
                # Проверяем grace period (3 дня)
                days_expired = (datetime.utcnow() - sub.expires_at).days

                if days_expired > 3:
                    await subscription_repo.expire(sub.id)
                    count += 1
                    logger.info(f"Expired subscription {sub.id}")

            await session.commit()

        logger.info(f"Expired {count} subscriptions")
        return count
