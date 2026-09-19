import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MemoryType(str, enum.Enum):
    PROGRESS = "PROGRESS"
    DELAY = "DELAY"
    RISK = "RISK"
    RECOVERY = "RECOVERY"
    WEATHER = "WEATHER"
    SAFETY = "SAFETY"
    QUALITY = "QUALITY"
    MATERIAL = "MATERIAL"
    EQUIPMENT = "EQUIPMENT"
    EVIDENCE = "EVIDENCE"
    MILESTONE = "MILESTONE"
    GENERAL = "GENERAL"
    WORKFORCE = "WORKFORCE"


class MemoryImportance(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProjectMemory(Base):
    __tablename__ = "project_memories"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_project_memory_event"),
        Index("ix_project_memories_project_date", "project_id", "memory_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("construction_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), index=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType, name="memory_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[MemoryImportance] = mapped_column(
        Enum(MemoryImportance, name="memory_importance"), nullable=False, index=True
    )
    memory_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[int] = mapped_column(nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship("Project")
    event = relationship("ConstructionEvent")
    activity = relationship("Activity")
