"""Обработчики регистрации и главного меню"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from mentorium_ai_client import MentorPrompt
from mentorium_db import get_platform_session, get_session
from mentorium_db.repositories import ParentRepository, PlatformRepository

from .states import RegistrationStates

if TYPE_CHECKING:
    from mentorium_ai_client import MentoriumAIClient

logger = logging.getLogger(__name__)

registration_router = Router(name="registration")


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Прогресс ребёнка"),
                KeyboardButton(text="💬 Задать вопрос"),
            ],
            [
                KeyboardButton(text="📈 Недельный отчёт"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def get_registration_method_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора способа регистрации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📧 Email ребёнка")],
            [KeyboardButton(text="🔑 Код привязки")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@registration_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, ai_client: MentoriumAIClient) -> None:
    """
    Обработчик команды /start
    
    Проверяет, зарегистрирован ли родитель:
    - Если да: показывает главное меню
    - Если нет: запускает процесс регистрации
    """
    if not message.from_user:
        return

    telegram_id = message.from_user.id

    # Проверяем, есть ли родитель в базе
    async with get_session() as session:
        repo = ParentRepository(session)
        parent = await repo.get_by_telegram_id(telegram_id)

        if parent:
            # Родитель уже зарегистрирован
            await message.answer(
                f"С возвращением, {message.from_user.first_name}! 👋\n\n"
                "Чем могу помочь?",
                reply_markup=get_main_menu_keyboard(),
            )

            # Генерируем приветствие от AI
            try:
                prompt = MentorPrompt(prompt="Родитель вернулся в бот. Коротко поприветствуй его.")
                reply = await ai_client.generate_reply(prompt, scenario="welcome")
                await message.answer(reply)
            except Exception as e:
                logger.error(f"Failed to generate welcome message: {e}")

            return

    # Родитель новый - начинаем регистрацию
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я — AI-наставник платформы Mentorium. Помогу вам отслеживать прогресс вашего ребёнка "
        "в обучении программированию, отвечу на вопросы и дам рекомендации.\n\n"
        "Для начала нужно привязать вашего ребёнка. Как вам удобнее?",
        reply_markup=get_registration_method_keyboard(),
    )

    await state.set_state(RegistrationStates.awaiting_email)


@registration_router.message(RegistrationStates.awaiting_email, F.text == "📧 Email ребёнка")
async def registration_method_email(message: Message, state: FSMContext) -> None:
    """Выбран способ регистрации через email"""
    await message.answer(
        "📧 Введите email, который ваш ребёнок использует на платформе Mentorium:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegistrationStates.awaiting_email)


@registration_router.message(RegistrationStates.awaiting_email, F.text == "🔑 Код привязки")
async def registration_method_code(message: Message, state: FSMContext) -> None:
    """Выбран способ регистрации через код"""
    await message.answer(
        "🔑 Введите код привязки, который можно найти в личном кабинете ребёнка:\n\n"
        "💡 Пример: ABC123",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegistrationStates.awaiting_code)


@registration_router.message(RegistrationStates.awaiting_email, F.text.contains("@"))
async def process_email(message: Message, state: FSMContext) -> None:
    """
    Обработка введённого email
    
    Проверяет, есть ли ученик с таким email в Platform DB
    """
    if not message.text or not message.from_user:
        return

    email = message.text.strip().lower()

    # Простая валидация email
    if "@" not in email or "." not in email:
        await message.answer(
            "❌ Некорректный email. Попробуйте ещё раз:\n\n"
            "Пример: student@example.com"
        )
        return

    # Ищем ученика в Platform DB
    async with get_platform_session() as platform_session:
        platform_repo = PlatformRepository(platform_session)
        student = await platform_repo.get_student_by_email(email)

        if not student:
            await message.answer(
                f"❌ Ученик с email {email} не найден на платформе Mentorium.\n\n"
                "Проверьте правильность email или используйте код привязки.",
                reply_markup=get_registration_method_keyboard(),
            )
            await state.set_state(RegistrationStates.awaiting_email)
            return

        # Ученик найден - сохраняем в state и запрашиваем подтверждение
        await state.update_data(student_id=student.id, student_name=student.first_name)

        await message.answer(
            f"✅ Найден ученик: {student.first_name} {student.last_name}\n\n"
            "Это ваш ребёнок?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Да, это он/она")],
                    [KeyboardButton(text="❌ Нет, ввести заново")],
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )

        await state.set_state(RegistrationStates.awaiting_confirmation)


@registration_router.message(RegistrationStates.awaiting_code)
async def process_code(message: Message, state: FSMContext) -> None:
    """
    Обработка введённого кода привязки
    
    Проверяет код в Platform DB
    """
    if not message.text or not message.from_user:
        return

    code = message.text.strip().upper()

    # Валидация кода (буквы и цифры, 6 символов)
    if len(code) != 6 or not code.isalnum():
        await message.answer(
            "❌ Некорректный код. Код должен содержать 6 символов (буквы и цифры).\n\n"
            "Пример: ABC123"
        )
        return

    # Проверяем код в Platform DB
    async with get_platform_session() as platform_session:
        platform_repo = PlatformRepository(platform_session)
        student = await platform_repo.validate_student_code(code)

        if not student:
            await message.answer(
                f"❌ Код {code} не найден или истёк.\n\n"
                "Проверьте код в личном кабинете ребёнка или используйте email.",
                reply_markup=get_registration_method_keyboard(),
            )
            await state.set_state(RegistrationStates.awaiting_email)
            return

        # Код валиден - сохраняем в state и запрашиваем подтверждение
        await state.update_data(student_id=student.id, student_name=student.first_name)

        await message.answer(
            f"✅ Найден ученик: {student.first_name} {student.last_name}\n\n"
            "Это ваш ребёнок?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Да, это он/она")],
                    [KeyboardButton(text="❌ Нет, ввести заново")],
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )

        await state.set_state(RegistrationStates.awaiting_confirmation)


@registration_router.message(RegistrationStates.awaiting_confirmation, F.text == "✅ Да, это он/она")
async def confirm_registration(
    message: Message, state: FSMContext, ai_client: MentoriumAIClient
) -> None:
    """
    Подтверждение регистрации
    
    Создаёт запись Parent и ParentStudent в Bot DB
    """
    if not message.from_user:
        return

    data = await state.get_data()
    student_id = data.get("student_id")
    student_name = data.get("student_name")

    if not student_id:
        await message.answer("❌ Произошла ошибка. Попробуйте ещё раз с /start")
        await state.clear()
        return

    telegram_id = message.from_user.id
    telegram_username = message.from_user.username

    # Создаём родителя в Bot DB
    async with get_session() as session:
        repo = ParentRepository(session)

        parent = await repo.create(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        # Привязываем ребёнка
        await repo.add_student(parent_id=parent.id, student_id=student_id)

        await session.commit()

    # Очищаем state
    await state.clear()

    # Отправляем приветствие
    await message.answer(
        f"🎉 Отлично! Вы успешно зарегистрированы.\n\n"
        f"Теперь я буду помогать вам следить за прогрессом {student_name} "
        "и отвечать на ваши вопросы о его обучении.",
        reply_markup=get_main_menu_keyboard(),
    )

    # Генерируем персональное приветствие от AI
    try:
        prompt = MentorPrompt(
            prompt=f"Родитель только что зарегистрировался. Его ребёнка зовут {student_name}. "
            "Тепло поприветствуй родителя, кратко расскажи о возможностях бота."
        )
        reply = await ai_client.generate_reply(prompt, scenario="welcome")
        await message.answer(reply)
    except Exception as e:
        logger.error(f"Failed to generate welcome message: {e}")


@registration_router.message(RegistrationStates.awaiting_confirmation, F.text == "❌ Нет, ввести заново")
async def cancel_confirmation(message: Message, state: FSMContext) -> None:
    """Отмена подтверждения - возврат к выбору способа регистрации"""
    await message.answer(
        "Хорошо, давайте попробуем ещё раз. Как вам удобнее?",
        reply_markup=get_registration_method_keyboard(),
    )
    await state.set_state(RegistrationStates.awaiting_email)


@registration_router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    """Команда для отображения главного меню"""
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


@registration_router.message(F.text == "⚙️ Настройки")
async def settings_handler(message: Message) -> None:
    """Обработчик кнопки настроек"""
    if not message.from_user:
        return

    async with get_session() as session:
        repo = ParentRepository(session)
        parent = await repo.get_by_telegram_id(message.from_user.id)

        if not parent:
            await message.answer("❌ Сначала нужно зарегистрироваться: /start")
            return

        students = await repo.get_students(parent.id)
        students_list = "\n".join([f"• {s.platform_student_id}" for s in students])

        await message.answer(
            f"⚙️ Ваши настройки:\n\n"
            f"👤 Telegram ID: {parent.telegram_id}\n"
            f"👶 Привязанные ученики:\n{students_list}\n\n"
            f"Для отвязки или добавления детей напишите в поддержку.",
            reply_markup=get_main_menu_keyboard(),
        )
