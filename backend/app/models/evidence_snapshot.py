from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.evidence import EvidenceStatus


class EvidenceSnapshot(Base):
    __tablename__ = "evidence_snapshots"
    __table_args__ = (
        Index("ix_evidence_snapshots_project_activity", "project_id", "activity_id"),
        Index("ix_evidence_snapshots_activity_captured", "activity_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    progress_reported: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    progress_ai_estimated: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    verification_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_snapshot_status"), nullable=False, index=True
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evidence = relationship("Evidence")
    activity = relationship("Activity")
