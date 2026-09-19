import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkforceAssignmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    ON_LEAVE = "ON_LEAVE"


class Crew(Base):
    __tablename__ = "crews"
    __table_args__ = (Index("ix_crews_project_active", "project_id", "is_active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    foreman_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    members = relationship("CrewMember", back_populates="crew", cascade="all, delete-orphan")
    foreman = relationship("User", foreign_keys=[foreman_id])


class CrewMember(Base):
    __tablename__ = "crew_members"
    __table_args__ = (UniqueConstraint("crew_id", "user_id", name="uq_crew_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(ForeignKey("crews.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    crew = relationship("Crew", back_populates="members")
    user = relationship("User")


class WorkerAssignment(Base):
    __tablename__ = "worker_assignments"
    __table_args__ = (
        UniqueConstraint("activity_id", "user_id", name="uq_worker_activity_user"),
        Index("ix_worker_assignments_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    crew_id: Mapped[int | None] = mapped_column(ForeignKey("crews.id", ondelete="SET NULL"), index=True)
    role: Mapped[str] = mapped_column(String(50), default="WORKER", nullable=False)
    status: Mapped[WorkforceAssignmentStatus] = mapped_column(
        Enum(WorkforceAssignmentStatus, name="workforce_assignment_status"),
        default=WorkforceAssignmentStatus.ACTIVE, nullable=False,
    )
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    activity = relationship("Activity")
    user = relationship("User", foreign_keys=[user_id])
    crew = relationship("Crew")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", "attendance_date", name="uq_attendance_project_user_date"),
        Index("ix_attendance_project_date", "project_id", "attendance_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"),
        default=AttendanceStatus.PRESENT, nullable=False,
    )
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_in_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    check_in_longitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    check_out_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    check_out_longitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")


# Public naming used by the workforce API and integrations.
WorkforceAssignment = WorkerAssignment
