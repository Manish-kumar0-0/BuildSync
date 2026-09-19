import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AIAnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        CheckConstraint(
            "estimated_progress >= 0 AND estimated_progress <= 100",
            name="ck_ai_analysis_estimated_progress_range",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_ai_analysis_confidence_score_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True, nullable=False
    )
    analysis_status: Mapped[AIAnalysisStatus] = mapped_column(
        Enum(AIAnalysisStatus, name="ai_analysis_status"),
        default=AIAnalysisStatus.PENDING,
        nullable=False,
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(150))
    estimated_progress: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    detected_elements: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    observations: Mapped[str | None] = mapped_column(Text)
    discrepancies: Mapped[Any | None] = mapped_column(JSON)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
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

    evidence = relationship("Evidence", back_populates="ai_analyses")
