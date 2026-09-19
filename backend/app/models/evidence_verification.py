import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EvidenceVerificationDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUEST_INFO = "REQUEST_INFO"


class EvidenceVerification(Base):
    __tablename__ = "evidence_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True, nullable=False
    )
    verified_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    decision: Mapped[EvidenceVerificationDecision] = mapped_column(
        Enum(EvidenceVerificationDecision, name="evidence_verification_decision"),
        nullable=False,
    )
    comments: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evidence = relationship("Evidence", back_populates="verifications")
    verifier = relationship("User", back_populates="evidence_verifications")
