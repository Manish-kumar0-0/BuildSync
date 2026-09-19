from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.construction_event import ConstructionEventType


class TimelineActor(BaseModel):
    id: int
    name: str


class TimelineLocation(BaseModel):
    latitude: Decimal | None
    longitude: Decimal | None
    gps_accuracy: Decimal | None


class TimelineEvent(BaseModel):
    id: int
    time: str
    event_type: ConstructionEventType
    title: str
    description: str | None
    actor: TimelineActor | None
    activity_id: int | None
    zone: str | None
    location: TimelineLocation


class ProjectTimelineResponse(BaseModel):
    project_id: int
    date: date | None
    start_date: date | None = None
    end_date: date | None = None
    page: int
    page_size: int
    total: int
    events: list[TimelineEvent]


class TimelineActivity(BaseModel):
    id: int
    name: str


class ActivityTimelineResponse(BaseModel):
    activity: TimelineActivity
    events: list[TimelineEvent]


class MajorTimelineEvent(BaseModel):
    event_id: int
    time: str
    type: ConstructionEventType
    title: str


class DailySummaryResponse(BaseModel):
    date: date
    total_events: int
    event_counts: dict[str, int]
    zones_active: list[str]
    activities_active: int
    activities_completed: int
    major_events: list[MajorTimelineEvent]
