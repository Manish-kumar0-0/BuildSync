from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models.construction_event import ConstructionEventType


class ReplayLocation(BaseModel):
    latitude: Decimal
    longitude: Decimal
    gps_accuracy: Decimal | None


class ReplayEvidenceReference(BaseModel):
    evidence_id: int
    file_type: str
    captured_at: datetime | None
    thumbnail_url: str | None = None


class ReplayEvent(BaseModel):
    sequence: int
    event_id: int
    timestamp: datetime
    relative_time_seconds: int
    event_type: ConstructionEventType
    title: str
    description: str | None
    activity_id: int | None
    zone: str | None
    location: ReplayLocation | None
    evidence_id: int | None
    evidence: ReplayEvidenceReference | None
    metadata: dict[str, Any] | None
    is_major_event: bool


class ReplayDuration(BaseModel):
    start: str | None
    end: str | None


class ReplaySummary(BaseModel):
    total_events: int
    first_event: str | None
    last_event: str | None
    activities_involved: int
    zones_involved: int
    major_events: int
    weather_interruptions: int
    risks_detected: int
    delays_predicted: int


class ReplayResponse(BaseModel):
    project_id: int
    date: date | None
    duration: ReplayDuration
    total_events: int
    events: list[ReplayEvent]
    summary: ReplaySummary
