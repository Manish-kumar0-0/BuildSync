import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import UserRole


class ProjectAssignmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ProjectUserAssignment(Base):
    __tablename__ = "project_user_assignments"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", "status", name="uq_project_user_assignment_status"),
        Index("ix_project_user_assignments_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="project_assignment_role"), nullable=False)
    status: Mapped[ProjectAssignmentStatus] = mapped_column(
        Enum(ProjectAssignmentStatus, name="project_assignment_status"),
        default=ProjectAssignmentStatus.ACTIVE, nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project")
    user = relationship("User")


class ProjectConfiguration(Base):
    __tablename__ = "project_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    default_zone: Mapped[str | None] = mapped_column(String(100))
    progress_update_frequency: Mapped[str] = mapped_column(String(30), default="DAILY", nullable=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    project = relationship("Project")


class ProjectZone(Base):
    __tablename__ = "project_zones"
    __table_args__ = (Index("ix_project_zones_project_active", "project_id", "active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_project_created", "project_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")
    user = relationship("User")
