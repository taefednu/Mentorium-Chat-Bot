from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, Field, HttpUrl


class ProgressTestScore(BaseModel):
    title: str
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100


class ParentProfile(BaseModel):
    parent_chat_id: str
    parent_email: str
    subscription_active: bool = True
    child_name: str | None = None
    last_payment_url: HttpUrl | None = None


class ProgressReport(BaseModel):
    learner_id: str
    parent: ParentProfile
    reporting_period: str
    strengths: Sequence[str] = Field(default_factory=list)
    focus_areas: Sequence[str] = Field(default_factory=list)
    upcoming_milestones: Sequence[str] = Field(default_factory=list)
    tests: Sequence[ProgressTestScore] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        lines: list[str] = [
            f"Отчет по ученику {self.learner_id} за период {self.reporting_period}",
            "Сильные стороны:",
            *self._format_bullets(self.strengths, fallback="- пока без обновлений."),
            "Зоны для внимания:",
            *self._format_bullets(self.focus_areas, fallback="- требуется уточнение."),
        ]

        if self.tests:
            lines.append("Результаты тестов:")
            for test in self.tests:
                lines.append(
                    f"- {test.title}: {test.score:.1f}/{test.max_score:.1f} ("
                    f"{test.percentage:.0f}%)"
                )

        if self.upcoming_milestones:
            lines.append("Предстоящие задания:")
            lines.extend(f"- {item}" for item in self.upcoming_milestones)

        lines.append("Спасибо, что вы с Mentorium! 💙")
        return "\n".join(lines)

    @staticmethod
    def _format_bullets(items: Sequence[str], fallback: str) -> list[str]:
        if not items:
            return [fallback]

        return [f"- {value}" for value in items]
