import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProgressAssessmentStatus(str, enum.Enum):
    ON_TRACK = "ON_TRACK"
    MINOR_VARIANCE = "MINOR_VARIANCE"
    SIGNIFICANT_VARIANCE = "SIGNIFICANT_VARIANCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ProgressAssessment(Base):
    __tablename__ = "progress_assessments"
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "assessment_date",
            name="uq_progress_assessment_activity_date",
        ),
        CheckConstraint(
            "planned_progress >= 0 AND planned_progress <= 100",
            name="ck_progress_assessment_planned_range",
        ),
        CheckConstraint(
            "reported_progress >= 0 AND reported_progress <= 100",
            name="ck_progress_assessment_reported_range",
        ),
        CheckConstraint(
            "ai_estimated_progress >= 0 AND ai_estimated_progress <= 100",
            name="ck_progress_assessment_ai_range",
        ),
        CheckConstraint(
            "ai_confidence >= 0 AND ai_confidence <= 100",
            name="ck_progress_assessment_confidence_range",
        ),
        CheckConstraint(
            "fused_progress >= 0 AND fused_progress <= 100",
            name="ck_progress_assessment_fused_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    schedule_activity_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_activities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), index=True
    )
    comparison_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_comparison_analyses.id", ondelete="SET NULL"),
        index=True,
    )
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    planned_progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    reported_progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    measured_progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ai_estimated_progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    fused_progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    variance_from_plan: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    variance_from_reported: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    assessment_status: Mapped[ProgressAssessmentStatus] = mapped_column(
        Enum(ProgressAssessmentStatus, name="progress_assessment_status"),
        nullable=False,
        index=True,
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project = relationship("Project")
    activity = relationship("Activity")
    schedule_activity = relationship("ScheduleActivity")
    evidence = relationship("Evidence")
    comparison = relationship("EvidenceComparisonAnalysis")
