import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeasuredProgressVerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ActivityMeasuredProgress(Base):
    __tablename__ = "activity_measured_progress"
    __table_args__ = (
        UniqueConstraint("activity_id", "assessment_date", name="uq_measured_progress_activity_date"),
        CheckConstraint("planned_quantity > 0", name="ck_measured_progress_planned_positive"),
        CheckConstraint("completed_quantity >= 0", name="ck_measured_progress_completed_nonnegative"),
        CheckConstraint("completed_quantity <= planned_quantity", name="ck_measured_progress_completed_lte_planned"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True, nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    completed_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[MeasuredProgressVerificationStatus] = mapped_column(
        Enum(MeasuredProgressVerificationStatus, name="measured_progress_verification_status"),
        default=MeasuredProgressVerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    verification_notes: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project")
    activity = relationship("Activity", back_populates="measured_progress")
    recorder = relationship(
        "User",
        foreign_keys=[recorded_by],
        back_populates="recorded_measured_progress",
    )
    verifier = relationship(
        "User",
        foreign_keys=[verified_by],
        back_populates="verified_measured_progress",
    )
