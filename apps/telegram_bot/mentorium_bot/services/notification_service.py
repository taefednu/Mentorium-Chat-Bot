"""
Сервис для отправки уведомлений родителям
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from aiogram import Bot

from mentorium_db import get_session
from mentorium_db.repositories import NotificationRepository, ParentRepository

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для создания и отправки уведомлений"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_test_completed_notification(
        self,
        parent_telegram_id: int,
        student_name: str,
        test_name: str,
        score: float,
    ) -> bool:
        """
        Уведомление о прохождении теста
        
        Args:
            parent_telegram_id: Telegram ID родителя
            student_name: Имя ученика
            test_name: Название теста
            score: Балл (0-100)
            
        Returns:
            True если отправлено успешно
        """
        if score >= 90:
            emoji = "⭐"
            comment = "отлично!"
        elif score >= 70:
            emoji = "✅"
            comment = "хорошо!"
        else:
            emoji = "💪"
            comment = "есть куда расти"

        message = (
            f"{emoji} {student_name} прошёл тест \"{test_name}\"\n"
            f"Результат: {score:.0f}% — {comment}"
        )

        try:
            await self.bot.send_message(parent_telegram_id, message)

            # Сохраняем в базу
            await self._save_notification(
                parent_telegram_id=parent_telegram_id,
                notification_type="TEST_COMPLETED",
                title=f"Тест: {test_name}",
                message=message,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")
            return False

    async def send_course_completed_notification(
        self,
        parent_telegram_id: int,
        student_name: str,
        course_name: str,
    ) -> bool:
        """Уведомление о завершении курса"""
        message = (
            f"🎉 Поздравляем! {student_name} завершил курс \"{course_name}\"\n\n"
            f"Сертификат готов в личном кабинете на платформе Mentorium."
        )

        try:
            await self.bot.send_message(parent_telegram_id, message)

            await self._save_notification(
                parent_telegram_id=parent_telegram_id,
                notification_type="COURSE_COMPLETED",
                title=f"Курс завершён: {course_name}",
                message=message,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to send course completion notification: {e}")
            return False

    async def send_inactivity_reminder(
        self,
        parent_telegram_id: int,
        student_name: str,
        days_inactive: int,
        days_without_skip: int,
    ) -> bool:
        """
        Напоминание о неактивности (если не заходил 3 дня)
        
        Args:
            parent_telegram_id: Telegram ID родителя
            student_name: Имя ученика
            days_inactive: Сколько дней не заходил
            days_without_skip: Текущий streak (дни без пропусков)
        """
        message = (
            f"⚠️ {student_name} не заходил на платформу {days_inactive} дня\n\n"
        )

        if days_without_skip > 0:
            message += f"Текущий рекорд 🔥{days_without_skip} дней может прерваться. Напомните ему!\n\n"

        message += "💡 Даже 15 минут в день помогают поддерживать прогресс"

        try:
            await self.bot.send_message(parent_telegram_id, message)

            await self._save_notification(
                parent_telegram_id=parent_telegram_id,
                notification_type="INACTIVITY_REMINDER",
                title=f"Неактивность: {days_inactive} дн.",
                message=message,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to send inactivity reminder: {e}")
            return False

    async def send_subscription_expiring_notification(
        self,
        parent_telegram_id: int,
        days_left: int,
    ) -> bool:
        """
        Напоминание об истечении подписки
        
        Args:
            parent_telegram_id: Telegram ID родителя
            days_left: Сколько дней осталось
        """
        message = (
            f"💳 Подписка заканчивается через {days_left} дня\n\n"
            f"Не забудьте продлить, чтобы продолжить обучение без перерыва.\n\n"
            f"[Продлить подписку] — команда /subscribe"
        )

        try:
            await self.bot.send_message(parent_telegram_id, message)

            await self._save_notification(
                parent_telegram_id=parent_telegram_id,
                notification_type="SUBSCRIPTION_EXPIRING",
                title=f"Подписка истекает через {days_left} дн.",
                message=message,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to send subscription expiring notification: {e}")
            return False

    async def send_new_course_notification(
        self,
        parent_telegram_id: int,
        student_name: str,
        course_name: str,
    ) -> bool:
        """Уведомление о новом доступном курсе"""
        message = (
            f"🆕 Новый курс \"{course_name}\" доступен на платформе!\n\n"
            f"Рекомендован для {student_name} на основе его прогресса.\n\n"
            f"Узнать больше: /courses"
        )

        try:
            await self.bot.send_message(parent_telegram_id, message)

            await self._save_notification(
                parent_telegram_id=parent_telegram_id,
                notification_type="NEW_COURSE",
                title=f"Новый курс: {course_name}",
                message=message,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to send new course notification: {e}")
            return False

    async def _save_notification(
        self,
        parent_telegram_id: int,
        notification_type: str,
        title: str,
        message: str,
    ) -> None:
        """Сохранить уведомление в базу данных"""
        try:
            async with get_session() as session:
                parent_repo = ParentRepository(session)
                parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

                if not parent:
                    logger.warning(f"Parent {parent_telegram_id} not found when saving notification")
                    return

                notification_repo = NotificationRepository(session)
                await notification_repo.create(
                    parent_id=parent.id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                )
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to save notification to DB: {e}")

    async def check_and_send_inactivity_reminders(self) -> int:
        """
        Проверить всех учеников на неактивность и отправить напоминания
        
        Вызывается по расписанию (раз в день)
        
        Returns:
            Количество отправленных уведомлений
        """
        # TODO: Реализовать после получения доступа к Platform DB
        # 1. Получить всех активных родителей
        # 2. Для каждого проверить last_login ученика
        # 3. Если > 3 дней — отправить напоминание
        logger.info("check_and_send_inactivity_reminders called (not implemented)")
        return 0

    async def check_and_send_subscription_reminders(self) -> int:
        """
        Проверить подписки и отправить напоминания об истечении
        
        Вызывается по расписанию (раз в день)
        
        Returns:
            Количество отправленных уведомлений
        """
        count = 0
        threshold_date = datetime.utcnow() + timedelta(days=3)

        async with get_session() as session:
            from mentorium_db.repositories import SubscriptionRepository

            subscription_repo = SubscriptionRepository(session)
            expiring_subs = await subscription_repo.get_expiring_soon(days_threshold=3)

            for sub in expiring_subs:
                parent_repo = ParentRepository(session)
                parent = await parent_repo.get_by_id(sub.parent_id)

                if not parent:
                    continue

                days_left = (sub.expires_at.date() - datetime.utcnow().date()).days

                success = await self.send_subscription_expiring_notification(
                    parent.telegram_id, days_left
                )

                if success:
                    count += 1

        logger.info(f"Sent {count} subscription expiring notifications")
        return count
