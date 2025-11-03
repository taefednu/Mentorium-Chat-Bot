from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import tiktoken
from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MentorPrompt:
    prompt: str
    conversation_id: str | None = None


@dataclass(slots=True)
class DialogMessage:
    """Сообщение в диалоге с AI"""

    role: str  # "user" или "assistant"
    content: str
    timestamp: str | None = None


@dataclass(slots=True)
class StudentContext:
    """Контекст ученика для формирования промпта"""

    student_name: str
    age: int | None
    courses: list[dict[str, Any]]  # [{"name": "Python", "progress": 45, "lessons_completed": 12}]
    recent_tests: list[dict[str, Any]]  # [{"name": "Variables", "score": 85, "passed": True}]
    activity_days: int
    last_activity: str | None


class MentoriumAIClient:
    """
    Клиент для работы с OpenAI API с улучшенной обработкой ошибок
    
    Features:
    - Automatic token counting и trimming
    - Retry logic для API errors
    - Rate limiting protection
    - Context formation из learner data
    - System prompts для разных сценариев
    """

    # Лимиты модели gpt-4o-mini
    MAX_CONTEXT_TOKENS = 128000
    MAX_COMPLETION_TOKENS = 4096
    TARGET_CONTEXT_TOKENS = 8000  # Безопасный лимит для контекста

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._encoding = tiktoken.encoding_for_model(model)

    def count_tokens(self, text: str) -> int:
        """Подсчёт количества токенов в тексте"""
        return len(self._encoding.encode(text))

    def trim_messages_to_fit(
        self, messages: list[dict[str, str]], max_tokens: int
    ) -> list[dict[str, str]]:
        """
        Обрезает историю сообщений до заданного лимита токенов
        
        Всегда сохраняет system prompt (первое сообщение)
        Удаляет старые сообщения из середины истории
        """
        if not messages:
            return []

        # System prompt всегда сохраняем
        system_msg = messages[0] if messages[0]["role"] == "system" else None
        user_messages = messages[1:] if system_msg else messages

        # Считаем токены
        system_tokens = self.count_tokens(system_msg["content"]) if system_msg else 0
        remaining_tokens = max_tokens - system_tokens

        # Берём последние сообщения, которые влезают в лимит
        trimmed = []
        current_tokens = 0

        for msg in reversed(user_messages):
            msg_tokens = self.count_tokens(msg["content"]) + 4  # +4 для метаданных
            if current_tokens + msg_tokens > remaining_tokens:
                break
            trimmed.insert(0, msg)
            current_tokens += msg_tokens

        result = [system_msg] if system_msg else []
        result.extend(trimmed)

        logger.info(
            f"Trimmed messages: {len(user_messages)} -> {len(trimmed)}, "
            f"tokens: {current_tokens + system_tokens}/{max_tokens}"
        )

        return result

    def build_system_prompt(
        self, scenario: str = "general", student_context: StudentContext | None = None
    ) -> str:
        """
        Формирует system prompt в зависимости от сценария
        
        Scenarios:
        - welcome: Приветствие нового родителя
        - progress: Вопросы о прогрессе ребёнка
        - recommendations: Запрос рекомендаций
        - general: Общий диалог (по умолчанию)
        """
        base = (
            "Ты — поддерживающий AI-наставник платформы Mentorium. "
            "Твоя задача — помогать родителям понимать прогресс их детей в обучении программированию, "
            "отвечать на вопросы о курсах, мотивировать и давать персонализированные рекомендации.\n\n"
            "Стиль общения:\n"
            "- Тёплый, дружелюбный, но профессиональный\n"
            "- Используй эмодзи умеренно (1-2 на сообщение)\n"
            "- Пиши короткими абзацами для удобного чтения в Telegram\n"
            "- Избегай технического жаргона, объясняй простыми словами\n"
            "- Если не знаешь точного ответа — честно скажи об этом\n\n"
        )

        if student_context:
            context_str = (
                f"Контекст ученика:\n"
                f"- Имя: {student_context.student_name}\n"
            )
            if student_context.age:
                context_str += f"- Возраст: {student_context.age} лет\n"
            if student_context.courses:
                context_str += "- Курсы:\n"
                for course in student_context.courses[:3]:  # Максимум 3 курса
                    context_str += (
                        f"  • {course['name']}: {course['progress']}% "
                        f"({course['lessons_completed']} уроков)\n"
                    )
            if student_context.recent_tests:
                context_str += "- Последние тесты:\n"
                for test in student_context.recent_tests[:3]:
                    status = "✅" if test["passed"] else "❌"
                    context_str += f"  • {test['name']}: {test['score']}% {status}\n"
            context_str += f"- Активных дней за месяц: {student_context.activity_days}\n\n"
            base += context_str

        if scenario == "welcome":
            base += (
                "Сейчас родитель только что зарегистрировался. Тепло поприветствуй его, "
                "кратко расскажи, что ты умеешь (отчёты, ответы на вопросы, рекомендации), "
                "и предложи задать первый вопрос."
            )
        elif scenario == "progress":
            base += (
                "Родитель интересуется прогрессом ребёнка. Проанализируй данные выше, "
                "отметь успехи, обрати внимание на зоны роста, дай 2-3 конкретных совета."
            )
        elif scenario == "recommendations":
            base += (
                "Родитель просит рекомендации по обучению. На основе данных ученика предложи: "
                "1) следующие темы для изучения, "
                "2) как мотивировать ребёнка, "
                "3) упражнения или проекты для практики."
            )

        return base

    @retry(
        retry=retry_if_exception_type((APIError, RateLimitError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
    )
    async def generate_reply(
        self,
        request: MentorPrompt,
        history: list[DialogMessage] | None = None,
        student_context: StudentContext | None = None,
        scenario: str = "general",
    ) -> str:
        """
        Генерирует ответ от AI-наставника с учётом контекста
        
        Args:
            request: Запрос с промптом
            history: История предыдущих сообщений (опционально)
            student_context: Данные ученика для контекста (опционально)
            scenario: Сценарий общения (welcome/progress/recommendations/general)
            
        Returns:
            Текст ответа от AI
            
        Raises:
            RuntimeError: Если получен пустой ответ
            APIError: При ошибках OpenAI API (после 3 попыток)
        """
        # Формируем system prompt
        system_prompt = self.build_system_prompt(scenario, student_context)

        # Собираем messages
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Добавляем историю
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        # Добавляем текущий запрос
        messages.append({"role": "user", "content": request.prompt})

        # Обрезаем до лимита токенов
        messages = self.trim_messages_to_fit(messages, self.TARGET_CONTEXT_TOKENS)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore
                max_tokens=self.MAX_COMPLETION_TOKENS,
                temperature=0.7,
            )

            message = response.choices[0].message.content
            if not message:
                raise RuntimeError("Получен пустой ответ от модели")

            logger.info(
                f"Generated reply: {len(message)} chars, "
                f"tokens used: {response.usage.total_tokens if response.usage else 'unknown'}"  # type: ignore
            )

            return message

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_reply: {e}")
            raise RuntimeError(f"Ошибка генерации ответа: {e}") from e
