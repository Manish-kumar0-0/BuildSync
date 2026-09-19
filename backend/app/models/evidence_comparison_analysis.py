from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EvidenceComparisonAnalysis(Base):
    __tablename__ = "evidence_comparison_analyses"
    __table_args__ = (
        Index(
            "ix_evidence_comparison_pair",
            "current_evidence_id",
            "previous_evidence_id",
        ),
        Index("ix_evidence_comparison_project_activity", "project_id", "activity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    comparison_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    overall_change: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    construction_change_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False
    )
    absolute_progress_estimate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    absolute_progress_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    observations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    possible_issues: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship("Project")
    activity = relationship("Activity")
    current_evidence = relationship("Evidence", foreign_keys=[current_evidence_id])
    previous_evidence = relationship("Evidence", foreign_keys=[previous_evidence_id])
