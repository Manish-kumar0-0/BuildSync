from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.safety import (
    SafetyIncidentSeverity, SafetyIncidentStatus, SafetyIncidentType,
)


class SafetyIncidentCreate(BaseModel):
    activity_id: int | None = Field(default=None, gt=0)
    incident_type: SafetyIncidentType
    severity: SafetyIncidentSeverity
    description: str = Field(min_length=1)
    zone: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class SafetyIncidentResponse(SafetyIncidentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    reported_by: int
    status: SafetyIncidentStatus
    created_at: datetime

    @field_validator("occurred_at", mode="before")
    @classmethod
    def normalize_database_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class SafetySummary(BaseModel):
    project_id: int
    total_incidents: int
    open_incidents: int
    critical_incidents: int
    incidents_by_severity: dict[str, int]
    incidents_by_type: dict[str, int]
