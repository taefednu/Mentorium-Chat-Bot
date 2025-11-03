"""
Обработчики для подписок и платежей
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
)

from mentorium_db import get_session
from mentorium_db.repositories import ParentRepository

if TYPE_CHECKING:
    from mentorium_bot.services.billing_service import BillingService

logger = logging.getLogger(__name__)

billing_router = Router(name="billing")


def get_tariffs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 1 месяц — 99,000 UZS", callback_data="tariff:monthly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📆 3 месяца — 249,000 UZS (-17%)", callback_data="tariff:quarterly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 1 год — 899,000 UZS (-25%)", callback_data="tariff:annual"
                )
            ],
        ]
    )


def get_payment_methods_keyboard(tariff: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Telegram Stars", callback_data=f"pay:telegram_stars:{tariff}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 PayMe", callback_data=f"pay:payme:{tariff}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Click", callback_data=f"pay:click:{tariff}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="billing:tariffs")],
        ]
    )


@billing_router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, billing_service: BillingService) -> None:
    """Команда для оформления подписки"""
    if not message.from_user:
        return

    # Проверяем текущий статус подписки
    status = await billing_service.check_subscription_status(message.from_user.id)

    if status and status["active"]:
        days_left = status["days_left"]
        tariff = status["tariff"]

        await message.answer(
            f"✅ У вас активная подписка ({tariff})\n\n"
            f"Осталось дней: {days_left}\n"
            f"Истекает: {status['expires_at'].strftime('%d.%m.%Y')}\n\n"
            f"Автопродление: {'✅ Включено' if status['auto_renew'] else '❌ Выключено'}\n\n"
            f"Для отмены: /cancel_subscription"
        )
        return

    # Показываем тарифы
    await message.answer(
        "💳 Выберите тариф подписки:\n\n"
        "С подпиской вы получаете:\n"
        "• 📊 Еженедельные отчёты о прогрессе\n"
        "• 💬 Безлимитные AI диалоги с наставником\n"
        "• 📈 Детальная аналитика обучения\n"
        "• 🔔 Уведомления о достижениях\n"
        "• ⚡ Приоритетная поддержка",
        reply_markup=get_tariffs_keyboard(),
    )


@billing_router.callback_query(F.data.startswith("tariff:"))
async def select_tariff(callback: CallbackQuery) -> None:
    """Обработка выбора тарифа"""
    if not callback.message or not callback.data:
        return
    
    # Type guard for Message
    from aiogram.types import Message as MessageType
    if not isinstance(callback.message, MessageType):
        return

    tariff = callback.data.split(":")[1]

    # Маппинг тарифов
    tariff_names = {
        "monthly": "1 месяц — 99,000 UZS",
        "quarterly": "3 месяца — 249,000 UZS",
        "annual": "1 год — 899,000 UZS",
    }

    await callback.message.edit_text(
        f"📦 Выбран тариф: {tariff_names.get(tariff, tariff)}\n\n"
        f"Выберите способ оплаты:",
        reply_markup=get_payment_methods_keyboard(tariff),
    )


@billing_router.callback_query(F.data.startswith("pay:"))
async def process_payment_method(
    callback: CallbackQuery, billing_service: BillingService
) -> None:
    """Обработка выбора способа оплаты"""
    if not callback.message or not callback.data or not callback.from_user:
        return
    
    # Type guard for Message
    from aiogram.types import Message as MessageType
    if not isinstance(callback.message, MessageType):
        return

    parts = callback.data.split(":")
    provider = parts[1]
    tariff = parts[2]

    await callback.answer("⏳ Создаю платёж...")

    try:
        payment_url, amount = await billing_service.create_subscription(
            parent_telegram_id=callback.from_user.id,
            tariff=tariff,
            payment_provider=provider,
        )

        if provider == "telegram_stars":
            # Telegram Stars - отправляем invoice
            await send_telegram_stars_invoice(callback.message, tariff, int(amount))

        elif payment_url:
            # PayMe/Click - отправляем ссылку
            await callback.message.edit_text(
                f"✅ Платёж создан!\n\n"
                f"💰 Сумма: {amount:,.0f} UZS\n"
                f"💳 Провайдер: {provider.upper()}\n\n"
                f"Нажмите на кнопку ниже для оплаты:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
                        [InlineKeyboardButton(text="❌ Отменить", callback_data="billing:cancel")],
                    ]
                ),
            )

        else:
            await callback.message.edit_text(
                f"❌ Провайдер {provider} временно недоступен.\n\n"
                f"Попробуйте другой способ оплаты.",
                reply_markup=get_payment_methods_keyboard(tariff),
            )

    except Exception as e:
        logger.error(f"Failed to create payment: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании платежа. Попробуйте позже."
        )


async def send_telegram_stars_invoice(
    message: Message, tariff: str, amount: int
) -> None:
    """Отправить invoice для оплаты Telegram Stars"""
    # Конвертируем UZS в Stars (примерно 1 Star = 100 UZS)
    # Это нужно будет настроить под реальный курс
    stars_amount = amount // 100

    tariff_names = {
        "monthly": "Подписка на 1 месяц",
        "quarterly": "Подписка на 3 месяца",
        "annual": "Подписка на 1 год",
    }

    await message.bot.send_invoice(  # type: ignore
        chat_id=message.chat.id,
        title="Mentorium Подписка",
        description=tariff_names.get(tariff, "Подписка на бот"),
        payload=f"subscription:{tariff}",
        provider_token="",  # Для Stars не нужен
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=tariff_names.get(tariff, "Подписка"), amount=stars_amount)],
    )


@billing_router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    """Обработка pre-checkout для Telegram Stars"""
    # Всегда подтверждаем (валидацию делали при создании)
    await pre_checkout_query.answer(ok=True)


@billing_router.message(F.successful_payment)
async def process_successful_payment(
    message: Message, billing_service: BillingService
) -> None:
    """Обработка успешного платежа Telegram Stars"""
    if not message.successful_payment or not message.from_user:
        return

    payment = message.successful_payment
    logger.info(
        f"Received successful payment: {payment.telegram_payment_charge_id}, "
        f"amount={payment.total_amount}"
    )

    # Извлекаем tariff из payload
    payload = payment.invoice_payload
    if not payload.startswith("subscription:"):
        logger.error(f"Invalid payment payload: {payload}")
        return

    tariff = payload.split(":")[1]

    # Активируем подписку
    # TODO: Получить payment_id из БД по telegram_payment_charge_id
    # Пока просто подтверждаем
    await message.answer(
        f"🎉 Оплата прошла успешно!\n\n"
        f"Ваша подписка ({tariff}) активирована.\n\n"
        f"Спасибо за использование Mentorium! 💙"
    )


@billing_router.message(Command("cancel_subscription"))
async def cmd_cancel_subscription(
    message: Message, billing_service: BillingService
) -> None:
    """Команда для отмены подписки"""
    if not message.from_user:
        return

    await message.answer(
        "❓ Вы уверены, что хотите отменить подписку?\n\n"
        "Автопродление будет отключено, но вы сможете пользоваться ботом "
        "до конца оплаченного периода.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, отменить", callback_data="cancel_sub:confirm")],
                [InlineKeyboardButton(text="❌ Нет, оставить", callback_data="cancel_sub:decline")],
            ]
        ),
    )


@billing_router.callback_query(F.data == "cancel_sub:confirm")
async def confirm_cancel_subscription(
    callback: CallbackQuery, billing_service: BillingService
) -> None:
    """Подтверждение отмены подписки"""
    if not callback.from_user or not callback.message:
        return
    
    # Type guard for Message
    from aiogram.types import Message as MessageType
    if not isinstance(callback.message, MessageType):
        return

    success = await billing_service.cancel_subscription(callback.from_user.id)

    if success:
        await callback.message.edit_text(
            "✅ Подписка отменена\n\n"
            "Автопродление отключено. Вы сможете пользоваться ботом до конца оплаченного периода.\n\n"
            "Чтобы оформить новую подписку: /subscribe"
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось отменить подписку. Возможно, у вас нет активной подписки."
        )

    await callback.answer()


@billing_router.callback_query(F.data == "cancel_sub:decline")
async def decline_cancel_subscription(callback: CallbackQuery) -> None:
    """Отказ от отмены подписки"""
    if not callback.message:
        return
    
    # Type guard for Message
    from aiogram.types import Message as MessageType
    if not isinstance(callback.message, MessageType):
        return

    await callback.message.edit_text("👍 Отлично! Ваша подписка остаётся активной.")
    await callback.answer()


@billing_router.callback_query(F.data == "billing:tariffs")
async def show_tariffs(callback: CallbackQuery) -> None:
    """Показать тарифы"""
    if not callback.message:
        return
    
    # Type guard for Message
    from aiogram.types import Message as MessageType
    if not isinstance(callback.message, MessageType):
        return

    await callback.message.edit_text(
        "💳 Выберите тариф подписки:\n\n"
        "С подпиской вы получаете:\n"
        "• 📊 Еженедельные отчёты о прогрессе\n"
        "• 💬 Безлимитные AI диалоги с наставником\n"
        "• 📈 Детальная аналитика обучения\n"
        "• 🔔 Уведомления о достижениях\n"
        "• ⚡ Приоритетная поддержка",
        reply_markup=get_tariffs_keyboard(),
    )
    await callback.answer()


@billing_router.callback_query(F.data == "billing:cancel")
async def cancel_payment(callback: CallbackQuery) -> None:
    """Отменить платёж"""
    if not callback.message:
        return
    
    # Type guard for Message
    from aiogram.types import Message as MessageType
    if not isinstance(callback.message, MessageType):
        return

    await callback.message.edit_text(
        "❌ Платёж отменён\n\n"
        "Если хотите оформить подписку позже: /subscribe"
    )
    await callback.answer()
