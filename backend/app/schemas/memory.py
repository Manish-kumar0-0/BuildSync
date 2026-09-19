from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models.project_memory import MemoryImportance, MemoryType


class MemoryEventResponse(BaseModel):
    id: int
    event_type: str
    event_timestamp: datetime
    title: str
    description: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    gps_accuracy: Decimal | None
    zone: str | None
    evidence_id: int | None


class ProjectMemoryResponse(BaseModel):
    id: int
    project_id: int
    event_id: int
    activity_id: int | None
    type: MemoryType
    importance: MemoryImportance
    title: str
    summary: str
    memory_date: date
    source_type: str
    source_id: int
    metadata: dict[str, Any] | None = None


class ProjectMemoryListResponse(BaseModel):
    project_id: int
    total: int
    memories: list[ProjectMemoryResponse]
    page: int
    page_size: int


class ProjectMemoryDetailResponse(ProjectMemoryResponse):
    event: MemoryEventResponse
    activity_name: str | None = None
    wbs_id: int | None = None
    wbs_name: str | None = None


class MemoryContextItem(BaseModel):
    date: date
    type: MemoryType
    summary: str


class MemoryContextResponse(BaseModel):
    project_id: int
    context: list[MemoryContextItem]
