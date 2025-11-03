"""Обработчики AI диалогов с родителями"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.types import Message

from mentorium_ai_client import DialogMessage, MentorPrompt, StudentContext
from mentorium_core.services.reporting import ParentReportBuilder
from mentorium_db import get_platform_session, get_session
from mentorium_db.repositories import (
    DialogRepository,
    ParentRepository,
    PlatformRepository,
    SqlReportRepository,
)

from .registration import get_main_menu_keyboard

if TYPE_CHECKING:
    from mentorium_ai_client import MentoriumAIClient

logger = logging.getLogger(__name__)

router = Router(name="dialog")


async def get_student_context_for_parent(
    parent_telegram_id: int,
) -> tuple[StudentContext | None, str | None]:
    """
    Получить контекст первого ученика родителя для AI
    
    Returns:
        (StudentContext, student_id) или (None, None) если ученик не найден
    """
    async with get_session() as session:
        parent_repo = ParentRepository(session)
        parent = await parent_repo.get_by_telegram_id(parent_telegram_id)

        if not parent:
            return None, None

        students = await parent_repo.get_students(parent.id)
        if not students:
            return None, None

        # Берём первого (или primary) ученика
        primary_student = next((s for s in students if s.is_primary), students[0])
        student_id = primary_student.platform_student_id

    # Получаем данные из Platform DB
    async with get_platform_session() as platform_session:
        platform_repo = PlatformRepository(platform_session)
        student = await platform_repo.get_student_by_id(student_id)

        if not student:
            return None, student_id

        # Получаем прогресс и тесты
        courses = await platform_repo.get_student_course_progress(student_id)
        tests = await platform_repo.get_student_test_results(student_id, limit=5)
        activity_days = await platform_repo.get_student_activity_days(student_id)

        # Формируем контекст
        context = StudentContext(
            student_name=student.first_name,
            age=student.age,
            courses=[
                {
                    "name": c.course_name,
                    "progress": c.progress_percent,
                    "lessons_completed": c.lessons_completed,
                }
                for c in courses
            ],
            recent_tests=[
                {"name": t.test_name, "score": t.score, "passed": t.passed} for t in tests
            ],
            activity_days=activity_days,
            last_activity=(
                courses[0].last_activity.isoformat() if courses and courses[0].last_activity else None
            ),
        )

        return context, student_id


@router.message(F.text == "📊 Прогресс ребёнка")
async def handle_progress_request(message: Message, ai_client: MentoriumAIClient) -> None:
    """Обработчик кнопки 'Прогресс ребёнка'"""
    if not message.from_user:
        return

    await message.answer("⏳ Анализирую данные...")

    try:
        # Получаем контекст ученика
        context, student_id = await get_student_context_for_parent(message.from_user.id)

        if not context:
            await message.answer(
                "❌ Не удалось получить данные ученика. "
                "Убедитесь, что вы привязали ребёнка в настройках."
            )
            return

        # Генерируем отчёт от AI
        prompt = MentorPrompt(
            prompt="Расскажи родителю о текущем прогрессе ребёнка. "
            "Отметь успехи, обрати внимание на зоны роста, дай 2-3 совета."
        )
        reply = await ai_client.generate_reply(prompt, scenario="progress", student_context=context)

        await message.answer(reply, reply_markup=get_main_menu_keyboard())

        # Сохраняем диалог
        async with get_session() as session:
            dialog_repo = DialogRepository(session)
            await dialog_repo.save_message(
                parent_telegram_id=message.from_user.id,
                role="user",
                content="Покажи прогресс ребёнка",
            )
            await dialog_repo.save_message(
                parent_telegram_id=message.from_user.id, role="assistant", content=reply
            )
            await session.commit()

    except Exception as e:
        logger.error(f"Error in handle_progress_request: {e}")
        await message.answer("❌ Произошла ошибка при анализе данных. Попробуйте позже.")


@router.message(F.text == "📈 Недельный отчёт")
async def handle_weekly_report(message: Message) -> None:
    """Обработчик кнопки 'Недельный отчёт'"""
    if not message.from_user:
        return

    chat_id = str(message.chat.id)

    try:
        async with get_session() as session:
            repository = SqlReportRepository(session)
            report_builder = ParentReportBuilder(repository)
            report = await report_builder.build(
                learner_id=chat_id,
                parent_chat_id=chat_id,
                period="текущую неделю",
            )

        await message.answer(report.summary(), reply_markup=get_main_menu_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_weekly_report: {e}")
        await message.answer("❌ Не удалось сформировать отчёт. Попробуйте позже.")


@router.message(F.text == "💬 Задать вопрос")
async def handle_ask_question(message: Message) -> None:
    """Обработчик кнопки 'Задать вопрос'"""
    await message.answer(
        "💬 Задайте ваш вопрос, и я постараюсь помочь!\n\n"
        "Примеры вопросов:\n"
        "• Как мотивировать ребёнка?\n"
        "• Какие темы сейчас изучает?\n"
        "• Стоит ли давать дополнительные задания?\n"
        "• Как проходят тесты?"
    )


@router.message()
async def handle_dialog(message: Message, ai_client: MentoriumAIClient) -> None:
    """
    Главный обработчик AI диалогов
    
    Принимает любые текстовые сообщения, сохраняет историю,
    формирует контекст и генерирует ответ от AI
    """
    if not message.text or not message.from_user:
        return

    telegram_id = message.from_user.id

    # Проверяем, зарегистрирован ли родитель
    async with get_session() as session:
        parent_repo = ParentRepository(session)
        parent = await parent_repo.get_by_telegram_id(telegram_id)

        if not parent:
            await message.answer(
                "❌ Сначала нужно зарегистрироваться: /start",
                reply_markup=get_main_menu_keyboard(),
            )
            return

    # Показываем индикатор набора
    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        # Получаем контекст ученика
        context, student_id = await get_student_context_for_parent(telegram_id)

        # Получаем историю диалогов (последние 10 сообщений)
        async with get_session() as session:
            dialog_repo = DialogRepository(session)
            history_records = await dialog_repo.get_recent_history(telegram_id, limit=10)

            # Конвертируем в DialogMessage
            history = [
                DialogMessage(
                    role=record.role,
                    content=record.content,
                    timestamp=record.timestamp.isoformat(),
                )
                for record in history_records
            ]

        # Генерируем ответ
        prompt = MentorPrompt(prompt=message.text)
        reply = await ai_client.generate_reply(
            prompt, history=history, student_context=context, scenario="general"
        )

        await message.answer(reply, reply_markup=get_main_menu_keyboard())

        # Сохраняем диалог
        async with get_session() as session:
            dialog_repo = DialogRepository(session)
            await dialog_repo.save_message(
                parent_telegram_id=telegram_id, role="user", content=message.text
            )
            await dialog_repo.save_message(
                parent_telegram_id=telegram_id, role="assistant", content=reply
            )
            await session.commit()

    except Exception as e:
        logger.error(f"Error in handle_dialog: {e}", exc_info=True)
        await message.answer(
            "❌ Извините, произошла ошибка при обработке вашего запроса. "
            "Попробуйте переформулировать вопрос или обратитесь в поддержку.",
            reply_markup=get_main_menu_keyboard(),
        )
