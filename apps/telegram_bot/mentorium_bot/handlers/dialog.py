from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from mentorium_ai_client import MentorPrompt, MentoriumAIClient
from mentorium_core.services.reporting import ParentReportBuilder
from mentorium_db import get_session
from mentorium_db.repositories import SqlReportRepository

router = Router(name="dialog")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "Здравствуйте! Я Mentorium-бот. Расскажу о прогрессе вашего ребенка, поделюсь советами"
        " и помогу оформить подписку. Просто напишите вопрос."
    )


@router.message(lambda msg: msg.text and "отчет" in msg.text.lower())
async def handle_report_request(message: Message) -> None:
    chat_id = str(message.chat.id)

    async with get_session() as session:
        repository = SqlReportRepository(session)
        report_builder = ParentReportBuilder(repository)
        report = await report_builder.build(
            learner_id=chat_id,
            parent_chat_id=chat_id,
            period="текущую неделю",
        )

    await message.answer(report.summary())


@router.message()
async def handle_dialog(message: Message) -> None:
    client: MentoriumAIClient | None = message.bot.get("ai_client")  # type: ignore[attr-defined]
    if client is None:
        await message.answer("Сервис временно недоступен, попробуйте позже.")
        return

    prompt = MentorPrompt(prompt=message.text or "")
    reply = await client.generate_reply(prompt)
    await message.answer(reply)
