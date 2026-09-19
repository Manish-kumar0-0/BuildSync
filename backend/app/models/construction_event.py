import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConstructionEventType(str, enum.Enum):
    USER_LOGIN = "USER_LOGIN"
    WORKER_ARRIVAL = "WORKER_ARRIVAL"
    WORK_START = "WORK_START"
    WORK_PAUSED = "WORK_PAUSED"
    WORK_RESUMED = "WORK_RESUMED"
    WORK_COMPLETED = "WORK_COMPLETED"
    WORKFORCE_ASSIGNED = "WORKFORCE_ASSIGNED"
    WORKFORCE_UNASSIGNED = "WORKFORCE_UNASSIGNED"
    ATTENDANCE_CHECK_IN = "ATTENDANCE_CHECK_IN"
    ATTENDANCE_CHECK_OUT = "ATTENDANCE_CHECK_OUT"
    ACTIVITY_CREATED = "ACTIVITY_CREATED"
    ACTIVITY_ASSIGNED = "ACTIVITY_ASSIGNED"
    PROGRESS_REPORTED = "PROGRESS_REPORTED"
    EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"
    EVIDENCE_COMPARISON_COMPLETED = "EVIDENCE_COMPARISON_COMPLETED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    AI_ANALYSIS_COMPLETED = "AI_ANALYSIS_COMPLETED"
    PROGRESS_ASSESSED = "PROGRESS_ASSESSED"
    RISK_DETECTED = "RISK_DETECTED"
    DELAY_PREDICTED = "DELAY_PREDICTED"
    RECOVERY_RECOMMENDED = "RECOVERY_RECOMMENDED"
    RECOVERY_ACCEPTED = "RECOVERY_ACCEPTED"
    RECOVERY_IMPLEMENTED = "RECOVERY_IMPLEMENTED"
    MATERIAL_RECEIVED = "MATERIAL_RECEIVED"
    MATERIAL_DISPATCHED = "MATERIAL_DISPATCHED"
    EQUIPMENT_ARRIVAL = "EQUIPMENT_ARRIVAL"
    EQUIPMENT_ISSUE = "EQUIPMENT_ISSUE"
    SAFETY_INCIDENT = "SAFETY_INCIDENT"
    QUALITY_INSPECTION = "QUALITY_INSPECTION"
    QUALITY_INSPECTION_FAILED = "QUALITY_INSPECTION_FAILED"
    QUALITY_DEFECT = "QUALITY_DEFECT"
    WEATHER_INTERRUPTION = "WEATHER_INTERRUPTION"
    MILESTONE_MISSED = "MILESTONE_MISSED"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class ConstructionEvent(Base):
    __tablename__ = "construction_events"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_event_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_event_longitude"),
        CheckConstraint("gps_accuracy >= 0", name="ck_event_gps_accuracy"),
        Index(
            "ix_construction_events_reference",
            "reference_type",
            "reference_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), index=True
    )
    wbs_id: Mapped[int | None] = mapped_column(
        ForeignKey("wbs.id", ondelete="SET NULL"), index=True
    )
    event_type: Mapped[ConstructionEventType] = mapped_column(
        Enum(ConstructionEventType, name="construction_event_type"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    gps_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), index=True
    )
    reference_type: Mapped[str | None] = mapped_column(String(100))
    reference_id: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    project = relationship("Project")
    activity = relationship("Activity")
    wbs = relationship("WBS")
    actor = relationship("User")
    evidence = relationship("Evidence")
