import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SiteDisruptionType(str, enum.Enum):
    WEATHER = "WEATHER"
    RAIN = "RAIN"
    HEAT = "HEAT"
    STORM = "STORM"
    HIGH_WIND = "HIGH_WIND"
    FLOODING = "FLOODING"
    LIGHTNING = "LIGHTNING"
    VISIBILITY = "VISIBILITY"
    OTHER = "OTHER"


class SiteDisruptionSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SiteDisruptionSource(str, enum.Enum):
    MANUAL = "MANUAL"
    WEATHER_API = "WEATHER_API"
    SYSTEM = "SYSTEM"


class SiteDisruption(Base):
    __tablename__ = "site_disruptions"
    __table_args__ = (
        Index("ix_site_disruptions_project_start", "project_id", "start_time"),
        Index("ix_site_disruptions_activity_start", "activity_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[SiteDisruptionType] = mapped_column(
        Enum(SiteDisruptionType, name="site_disruption_type"),
        nullable=False,
        index=True,
    )
    severity: Mapped[SiteDisruptionSeverity] = mapped_column(
        Enum(SiteDisruptionSeverity, name="site_disruption_severity"),
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    duration_minutes: Mapped[int | None] = mapped_column()
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[SiteDisruptionSource] = mapped_column(
        Enum(SiteDisruptionSource, name="site_disruption_source"),
        nullable=False,
        default=SiteDisruptionSource.MANUAL,
        index=True,
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship("Project")
    activity = relationship("Activity")
    creator = relationship("User")
