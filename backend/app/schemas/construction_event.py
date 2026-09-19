from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.construction_event import ConstructionEventType


class ConstructionEventCreate(BaseModel):
    project_id: int = Field(gt=0)
    activity_id: int | None = Field(default=None, gt=0)
    wbs_id: int | None = Field(default=None, gt=0)
    event_type: ConstructionEventType
    event_timestamp: datetime
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    gps_accuracy: Decimal | None = Field(default=None, ge=0)
    zone: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    metadata: dict[str, Any] | None = None
    evidence_id: int | None = Field(default=None, gt=0)
    reference_type: str | None = Field(default=None, max_length=100)
    reference_id: int | None = Field(default=None, gt=0)


class EventUserResponse(BaseModel):
    id: int
    full_name: str
    role: str


class EventActivityResponse(BaseModel):
    id: int
    name: str
    activity_code: str


class EventWBSResponse(BaseModel):
    id: int
    name: str
    wbs_code: str


class EventEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    status: str


class ConstructionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    activity_id: int | None
    wbs_id: int | None
    event_type: ConstructionEventType
    actor_user_id: int | None
    event_timestamp: datetime
    latitude: Decimal | None
    longitude: Decimal | None
    gps_accuracy: Decimal | None
    zone: str | None
    title: str
    description: str | None
    metadata: dict[str, Any] | None = Field(
        default=None, validation_alias="event_metadata"
    )
    evidence_id: int | None
    reference_type: str | None
    reference_id: int | None
    created_at: datetime
    actor: EventUserResponse | None = None
    activity: EventActivityResponse | None = None
    wbs: EventWBSResponse | None = None
    evidence: EventEvidenceResponse | None = None


class ConstructionEventListResponse(BaseModel):
    items: list[ConstructionEventResponse]
    page: int
    page_size: int
    total: int
