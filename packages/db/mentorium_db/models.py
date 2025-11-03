from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Learner(Base):
    __tablename__ = "learners"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    parent_email: Mapped[str] = mapped_column(String(255))

    parent_chat: Mapped["ParentChat"] = relationship("ParentChat", back_populates="learner")
    reports: Mapped[list["ProgressReport"]] = relationship(
        "ProgressReport",
        back_populates="learner",
        cascade="all, delete-orphan",
    )


class ParentChat(Base):
    __tablename__ = "parent_chats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    learner: Mapped[Learner] = relationship("Learner", back_populates="parent_chat")


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"))
    reporting_period: Mapped[str] = mapped_column(String(50))
    strengths: Mapped[str] = mapped_column(Text)
    focus_areas: Mapped[str] = mapped_column(Text)
    milestones: Mapped[str] = mapped_column(Text)
    tests_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    learner: Mapped[Learner] = relationship("Learner", back_populates="reports")


class SubscriptionInvoice(Base):
    __tablename__ = "subscription_invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_email: Mapped[str] = mapped_column(String(255))
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    external_ref: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None]
