import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    WORKER = "WORKER"
    FOREMAN = "FOREMAN"
    FIELD_ENGINEER = "FIELD_ENGINEER"
    SITE_ENGINEER = "SITE_ENGINEER"
    SAFETY_OFFICER = "SAFETY_OFFICER"
    QA_QC_ENGINEER = "QA_QC_ENGINEER"
    MATERIAL_MANAGER = "MATERIAL_MANAGER"
    DRIVER = "DRIVER"
    EQUIPMENT_MANAGER = "EQUIPMENT_MANAGER"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.WORKER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    activity_assignments = relationship(
        "ActivityAssignment",
        foreign_keys="ActivityAssignment.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    uploaded_evidence = relationship(
        "Evidence",
        foreign_keys="Evidence.uploaded_by",
        back_populates="uploader",
    )
    evidence_verifications = relationship(
        "EvidenceVerification",
        foreign_keys="EvidenceVerification.verified_by",
        back_populates="verifier",
    )
    recorded_measured_progress = relationship(
        "ActivityMeasuredProgress",
        foreign_keys="ActivityMeasuredProgress.recorded_by",
        back_populates="recorder",
    )
    verified_measured_progress = relationship(
        "ActivityMeasuredProgress",
        foreign_keys="ActivityMeasuredProgress.verified_by",
        back_populates="verifier",
    )
