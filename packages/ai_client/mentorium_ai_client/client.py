from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI


@dataclass(slots=True)
class MentorPrompt:
    prompt: str
    conversation_id: str | None = None


class MentoriumAIClient:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate_reply(self, request: MentorPrompt) -> str:
        response = await self._client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Ты — поддерживающий наставник Mentorium. Общайся тепло, профессионально,"
                        " помогай родителям понимать прогресс ребенка и предлагай шаги развития."
                    ),
                },
                {
                    "role": "user",
                    "content": request.prompt,
                },
            ],
            metadata={"conversation_id": request.conversation_id} if request.conversation_id else None,
        )

        message = response.output[0].content[0].text if response.output else None
        if not message:
            raise RuntimeError("Получен пустой ответ от модели")

        return message
