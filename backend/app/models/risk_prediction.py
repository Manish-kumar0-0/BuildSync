import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PrimaryRisk(str, enum.Enum):
    PROGRESS_LAG = "PROGRESS_LAG"
    LOW_AI_CONFIDENCE = "LOW_AI_CONFIDENCE"
    DECLINING_PROGRESS = "DECLINING_PROGRESS"
    NOT_STARTED = "NOT_STARTED"
    LOW_PRODUCTIVITY = "LOW_PRODUCTIVITY"
    MISSED_MILESTONE = "MISSED_MILESTONE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    RESOURCE_CONSTRAINT = "RESOURCE_CONSTRAINT"
    WEATHER = "WEATHER"
    EQUIPMENT = "EQUIPMENT"
    MATERIAL = "MATERIAL"
    QUALITY = "QUALITY"
    SAFETY = "SAFETY"
    UNKNOWN = "UNKNOWN"


class RiskPredictionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ActivityRiskPrediction(Base):
    __tablename__ = "activity_risk_predictions"
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_activity_risk_prediction_score_range",
        ),
        CheckConstraint(
            "predicted_delay_days >= 0",
            name="ck_activity_risk_prediction_delay_non_negative",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_activity_risk_prediction_confidence_range",
        ),
        Index(
            "ix_activity_risk_prediction_project_date",
            "project_id",
            "prediction_date",
        ),
        Index(
            "ix_activity_risk_prediction_activity_date",
            "activity_id",
            "prediction_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schedule_activity_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comparison_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_comparison_analyses.id", ondelete="SET NULL"),
        index=True,
    )
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    predicted_delay_days: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    primary_risk: Mapped[PrimaryRisk] = mapped_column(
        Enum(PrimaryRisk, name="primary_risk"),
        nullable=False,
    )
    risk_factors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    explanation: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String(150))
    model_version: Mapped[str | None] = mapped_column(String(50))
    prediction_status: Mapped[RiskPredictionStatus] = mapped_column(
        Enum(RiskPredictionStatus, name="risk_prediction_status"),
        nullable=False,
        default=RiskPredictionStatus.PENDING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project = relationship("Project", back_populates="risk_predictions")
    activity = relationship("Activity", back_populates="risk_predictions")
    schedule_activity = relationship("ScheduleActivity")
    comparison = relationship("EvidenceComparisonAnalysis")
