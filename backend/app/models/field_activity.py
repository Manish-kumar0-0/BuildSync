import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.risk_prediction import ActivityRiskPrediction
    from app.models.activity_measured_progress import ActivityMeasuredProgress


class FieldActivityStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AI_ANALYZED = "AI_ANALYZED"
    VERIFIED = "VERIFIED"
    COMPLETED = "COMPLETED"


class AssignmentRole(str, enum.Enum):
    WORKER = "WORKER"
    FOREMAN = "FOREMAN"
    FIELD_ENGINEER = "FIELD_ENGINEER"
    SITE_ENGINEER = "SITE_ENGINEER"


class AssignmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    schedule_activity_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_activities.id", ondelete="CASCADE"), index=True
    )
    wbs_id: Mapped[int | None] = mapped_column(ForeignKey("wbs.id", ondelete="SET NULL"))
    boq_item_id: Mapped[int | None] = mapped_column(ForeignKey("boq_items.id", ondelete="SET NULL"))
    activity_code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[FieldActivityStatus] = mapped_column(
        Enum(FieldActivityStatus, name="field_activity_status"),
        default=FieldActivityStatus.NOT_STARTED,
        index=True,
    )
    progress_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    required_workers: Mapped[int | None] = mapped_column(Integer)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    responsible_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project", back_populates="field_activities")
    schedule_activity = relationship("ScheduleActivity", back_populates="field_activities")
    wbs = relationship("WBS", back_populates="field_activities")
    boq_item = relationship("BOQItem", back_populates="field_activities")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    responsible_user = relationship("User", foreign_keys=[responsible_user_id])
    assignments: Mapped[list["ActivityAssignment"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan"
    )
    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan"
    )
    risk_predictions: Mapped[list["ActivityRiskPrediction"]] = relationship(
        "ActivityRiskPrediction",
        back_populates="activity",
        cascade="all, delete-orphan",
    )
    measured_progress: Mapped[list["ActivityMeasuredProgress"]] = relationship(
        "ActivityMeasuredProgress", back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityAssignment(Base):
    __tablename__ = "activity_assignments"
    __table_args__ = (UniqueConstraint("activity_id", "user_id", name="uq_activity_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assignment_role: Mapped[AssignmentRole] = mapped_column(
        Enum(AssignmentRole, name="assignment_role"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"),
        default=AssignmentStatus.ACTIVE,
        nullable=False,
    )

    activity = relationship("Activity", back_populates="assignments")
    user = relationship("User", foreign_keys=[user_id])
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
