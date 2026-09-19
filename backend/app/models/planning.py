import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.field_activity import Activity
from app.models.user import User

if TYPE_CHECKING:
    from app.models.risk_prediction import ActivityRiskPrediction


class ProjectStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class WBSStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"


class ActivityStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"


class ScheduleApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    client: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(255))
    package_name: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date] = mapped_column(Date)
    planned_end_date: Mapped[date] = mapped_column(Date)
    actual_end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"), default=ProjectStatus.PLANNING
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    creator: Mapped[User | None] = relationship()
    wbs_items: Mapped[list["WBS"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    boq_items: Mapped[list["BOQItem"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    schedule_activities: Mapped[list["ScheduleActivity"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    field_activities: Mapped[list["Activity"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    field_activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="project", cascade="all, delete-orphan"
    )
    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    risk_predictions: Mapped[list["ActivityRiskPrediction"]] = relationship(
        "ActivityRiskPrediction",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class WBS(Base):
    __tablename__ = "wbs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    wbs_code: Mapped[str] = mapped_column(String(50))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("wbs.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    level: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[WBSStatus] = mapped_column(
        Enum(WBSStatus, name="wbs_status"), default=WBSStatus.PLANNED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="wbs_items")
    parent: Mapped["WBS | None"] = relationship(remote_side="WBS.id", back_populates="children")
    children: Mapped[list["WBS"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    boq_items: Mapped[list["BOQItem"]] = relationship(back_populates="wbs")
    schedule_activities: Mapped[list["ScheduleActivity"]] = relationship(back_populates="wbs")
    field_activities: Mapped[list["Activity"]] = relationship(back_populates="wbs")
    field_activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="wbs"
    )


class BOQItem(Base):
    __tablename__ = "boq_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    wbs_id: Mapped[int | None] = mapped_column(ForeignKey("wbs.id", ondelete="SET NULL"))
    item_code: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(30))
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    rate: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    planned_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="boq_items")
    wbs: Mapped[WBS | None] = relationship(back_populates="boq_items")
    field_activities: Mapped[list["Activity"]] = relationship(back_populates="boq_item")
    field_activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="boq_item"
    )


class ScheduleActivity(Base):
    __tablename__ = "schedule_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    wbs_id: Mapped[int | None] = mapped_column(ForeignKey("wbs.id", ondelete="SET NULL"))
    boq_item_id: Mapped[int | None] = mapped_column(ForeignKey("boq_items.id", ondelete="SET NULL"))
    activity_code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    planned_start: Mapped[date] = mapped_column(Date)
    planned_finish: Mapped[date] = mapped_column(Date)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))
    planned_progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    weightage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus, name="activity_status"), default=ActivityStatus.NOT_STARTED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    schedule_approval_status: Mapped[ScheduleApprovalStatus] = mapped_column(
        Enum(ScheduleApprovalStatus, name="schedule_approval_status"),
        default=ScheduleApprovalStatus.PENDING,
        nullable=False,
    )
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="schedule_activities")
    wbs: Mapped[WBS | None] = relationship(back_populates="schedule_activities")
    boq_item: Mapped[BOQItem | None] = relationship()
    planned_progress_points: Mapped[list["PlannedProgress"]] = relationship(
        back_populates="schedule_activity", cascade="all, delete-orphan"
    )
    field_activities: Mapped[list["Activity"]] = relationship(back_populates="schedule_activity")
    field_activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="schedule_activity"
    )
    approver = relationship("User", foreign_keys=[approved_by])


class PlannedProgress(Base):
    __tablename__ = "planned_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_activity_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_activities.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    planned_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3))

    schedule_activity: Mapped[ScheduleActivity] = relationship(
        back_populates="planned_progress_points"
    )
