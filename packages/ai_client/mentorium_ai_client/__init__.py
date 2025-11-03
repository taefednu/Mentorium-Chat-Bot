"""Адаптер для работы с OpenAI Chat API."""

from .client import (
    DialogMessage,
    MentoriumAIClient,
    MentorPrompt,
    StudentContext,
)

__all__ = [
    "MentoriumAIClient",
    "MentorPrompt",
    "DialogMessage",
    "StudentContext",
]
