import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    RISK = "RISK"
    DELAY = "DELAY"
    SAFETY = "SAFETY"
    QUALITY = "QUALITY"
    MATERIAL = "MATERIAL"
    EQUIPMENT = "EQUIPMENT"
    WORKFORCE = "WORKFORCE"
    EVIDENCE = "EVIDENCE"
    CRITICAL_RISK = "CRITICAL_RISK"
    HIGH_RISK = "HIGH_RISK"
    ACTIVITY_DELAY = "ACTIVITY_DELAY"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    RECOVERY_RECOMMENDATION = "RECOVERY_RECOMMENDATION"
    RECOVERY_ACCEPTED = "RECOVERY_ACCEPTED"
    MILESTONE_MISSED = "MILESTONE_MISSED"
    SYSTEM = "SYSTEM"


class NotificationPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False, index=True
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority, name="notification_priority"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(100), index=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project")
    recipient = relationship("User")
    activity = relationship("Activity")
