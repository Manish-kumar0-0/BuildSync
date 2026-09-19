import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InspectionType(str, enum.Enum):
    MATERIAL = "MATERIAL"
    WORKMANSHIP = "WORKMANSHIP"
    STRUCTURAL = "STRUCTURAL"
    DIMENSIONAL = "DIMENSIONAL"
    SAFETY = "SAFETY"
    GENERAL = "GENERAL"


class InspectionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CONDITIONAL = "CONDITIONAL"


class QualitySeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QualityDefectStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class QualityInspection(Base):
    __tablename__ = "quality_inspections"
    __table_args__ = (
        Index("ix_quality_inspections_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), index=True)
    inspector_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    inspection_type: Mapped[InspectionType] = mapped_column(Enum(InspectionType, name="inspection_type"), nullable=False)
    status: Mapped[InspectionStatus] = mapped_column(Enum(InspectionStatus, name="inspection_status"), default=InspectionStatus.PENDING, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")
    activity = relationship("Activity")
    inspector = relationship("User")
    defects = relationship("QualityDefect", back_populates="inspection", cascade="all, delete-orphan")


class QualityDefect(Base):
    __tablename__ = "quality_defects"
    __table_args__ = (
        Index("ix_quality_defects_project_status", "project_id", "status"),
        Index("ix_quality_defects_project_severity", "project_id", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), index=True)
    inspection_id: Mapped[int | None] = mapped_column(ForeignKey("quality_inspections.id", ondelete="SET NULL"), index=True)
    severity: Mapped[QualitySeverity] = mapped_column(Enum(QualitySeverity, name="quality_severity"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[QualityDefectStatus] = mapped_column(Enum(QualityDefectStatus, name="quality_defect_status"), default=QualityDefectStatus.OPEN, nullable=False)
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")
    activity = relationship("Activity")
    inspection = relationship("QualityInspection", back_populates="defects")
    reporter = relationship("User")
