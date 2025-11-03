from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


# === Модели для платформы (read-only, живут в platform DB) ===
class Learner(Base):
    """Ученик из платформы Mentorium (read-only)"""

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


# === Модели для бота (read-write, живут в bot DB) ===
class Parent(Base):
    """Родитель, зарегистрированный в боте"""

    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(100))
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    students: Mapped[list["ParentStudent"]] = relationship(
        "ParentStudent", back_populates="parent", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="parent", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="parent")
    dialog_messages: Mapped[list["DialogMessage"]] = relationship(
        "DialogMessage", back_populates="parent", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="parent", cascade="all, delete-orphan"
    )
    event_logs: Mapped[list["EventLog"]] = relationship(
        "EventLog", back_populates="parent", cascade="all, delete-orphan"
    )


class ParentStudent(Base):
    """Связь родителя с учеником из платформы"""

    __tablename__ = "parent_students"
    __table_args__ = (
        Index("ix_parent_students_parent_platform", "parent_id", "platform_student_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    platform_student_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="ID ученика из platform DB"
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Основной ребёнок для этого родителя"
    )

    # Relationships
    parent: Mapped[Parent] = relationship("Parent", back_populates="students")


class Subscription(Base):
    """Подписка родителя"""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="PENDING, ACTIVE, EXPIRED, CANCELLED",
    )
    tariff: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="MONTHLY, YEARLY или другие тарифы"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="Сумма в UZS")
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    parent: Mapped[Parent] = relationship("Parent", back_populates="subscriptions")


class Payment(Base):
    """История платежей"""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, comment="ID транзакции от провайдера"
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False, comment="PAYME, CLICK")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UZS")
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="PENDING, SUCCESS, FAILED, CANCELLED, REFUNDED",
    )
    external_ref: Mapped[str | None] = mapped_column(
        String(255), comment="Дополнительная референс-информация"
    )
    payment_metadata: Mapped[str | None] = mapped_column(Text, comment="JSON с деталями платежа")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    parent: Mapped[Parent] = relationship("Parent", back_populates="payments")


class DialogMessage(Base):
    """История диалогов с AI"""

    __tablename__ = "dialog_messages"
    __table_args__ = (Index("ix_dialog_messages_parent_timestamp", "parent_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="user, assistant, system")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, comment="Количество токенов")
    model: Mapped[str | None] = mapped_column(String(50), comment="gpt-4, gpt-3.5-turbo и т.д.")
    prompt_version: Mapped[str | None] = mapped_column(
        String(50), comment="Версия промпта для A/B тестов"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    parent: Mapped[Parent] = relationship("Parent", back_populates="dialog_messages")


class EventLog(Base):
    """Лог событий для аналитики и аудита"""

    __tablename__ = "event_logs"
    __table_args__ = (Index("ix_event_logs_type_timestamp", "event_type", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PARENT_REGISTERED, STUDENT_LINKED, DIALOG_STARTED, PAYMENT_SUCCESS и т.д.",
    )
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), index=True)
    platform_student_id: Mapped[str | None] = mapped_column(
        String(255), comment="ID ученика из platform DB"
    )
    payload: Mapped[str | None] = mapped_column(Text, comment="JSON с деталями события")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    parent: Mapped[Parent | None] = relationship("Parent", back_populates="event_logs")


class Notification(Base):
    """Уведомления для родителей"""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_parent_sent", "parent_id", "sent_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="TEST_COMPLETED, SUBSCRIPTION_EXPIRING, NEW_COURSE, INACTIVITY_REMINDER",
    )
    title: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    parent: Mapped[Parent] = relationship("Parent", back_populates="notifications")


# === Legacy/старые модели (сохраняем для совместимости) ===
class ParentChat(Base):
    """Legacy: старая модель ParentChat"""

    __tablename__ = "parent_chats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    learner: Mapped[Learner] = relationship("Learner", back_populates="parent_chat")


class ProgressReport(Base):
    """Отчёты о прогрессе ученика"""

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
    """Legacy: старая модель инвойсов"""

    __tablename__ = "subscription_invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_email: Mapped[str] = mapped_column(String(255))
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    external_ref: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None]
