import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecommendationType(str, enum.Enum):
    ADD_WORKFORCE = "ADD_WORKFORCE"
    EXTEND_SHIFT = "EXTEND_SHIFT"
    ADD_EQUIPMENT = "ADD_EQUIPMENT"
    EXPEDITE_MATERIAL = "EXPEDITE_MATERIAL"
    RESEQUENCE_ACTIVITY = "RESEQUENCE_ACTIVITY"
    INCREASE_MONITORING = "INCREASE_MONITORING"
    QUALITY_REVIEW = "QUALITY_REVIEW"
    SAFETY_REVIEW = "SAFETY_REVIEW"
    NO_ACTION = "NO_ACTION"


class RecommendationPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationImpact(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ImplementationEffort(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendationStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"


class RecoveryRecommendation(Base):
    __tablename__ = "recovery_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_prediction_id: Mapped[int] = mapped_column(
        ForeignKey("activity_risk_predictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType, name="recommendation_type"), nullable=False, index=True
    )
    priority: Mapped[RecommendationPriority] = mapped_column(
        Enum(RecommendationPriority, name="recommendation_priority"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[RecommendationImpact] = mapped_column(
        Enum(RecommendationImpact, name="recommendation_impact"), nullable=False
    )
    estimated_cost_impact: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    implementation_effort: Mapped[ImplementationEffort] = mapped_column(
        Enum(ImplementationEffort, name="implementation_effort"), nullable=False
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status"),
        nullable=False,
        default=RecommendationStatus.SUGGESTED,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project")
    activity = relationship("Activity")
    risk_prediction = relationship("ActivityRiskPrediction")
