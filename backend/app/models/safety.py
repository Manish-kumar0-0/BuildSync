import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SafetyIncidentType(str, enum.Enum):
    HAZARD = "HAZARD"
    NEAR_MISS = "NEAR_MISS"
    INCIDENT = "INCIDENT"
    ACCIDENT = "ACCIDENT"
    PPE_VIOLATION = "PPE_VIOLATION"


class SafetyIncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyIncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"


class PPEInspection(Base):
    __tablename__ = "ppe_inspections"
    __table_args__ = (Index("ix_ppe_inspections_project_date", "project_id", "inspection_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violation_type: Mapped[str | None] = mapped_column(String(100))
    inspected_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    worker = relationship("User", foreign_keys=[worker_id])
    inspector = relationship("User", foreign_keys=[inspected_by])


class SafetyIncident(Base):
    __tablename__ = "safety_incidents"
    __table_args__ = (
        Index("ix_safety_incidents_project_status", "project_id", "status"),
        Index("ix_safety_incidents_project_severity", "project_id", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), index=True)
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    incident_type: Mapped[SafetyIncidentType] = mapped_column(Enum(SafetyIncidentType, name="safety_incident_type"), nullable=False)
    severity: Mapped[SafetyIncidentSeverity] = mapped_column(Enum(SafetyIncidentSeverity, name="safety_incident_severity"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    zone: Mapped[str | None] = mapped_column(String(100))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[SafetyIncidentStatus] = mapped_column(Enum(SafetyIncidentStatus, name="safety_incident_status"), default=SafetyIncidentStatus.OPEN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")
    activity = relationship("Activity")
    reporter = relationship("User")
