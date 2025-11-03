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
        """
        Генерирует ответ от AI-наставника
        
        Args:
            request: Запрос с промптом и опциональным conversation_id
            
        Returns:
            Текст ответа от AI
            
        Raises:
            RuntimeError: Если получен пустой ответ от модели
        """
        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
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
        )

        message = response.choices[0].message.content
        if not message:
            raise RuntimeError("Получен пустой ответ от модели")

        return message
