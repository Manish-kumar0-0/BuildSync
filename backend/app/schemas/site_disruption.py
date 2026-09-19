from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.site_disruption import (
    SiteDisruptionSeverity,
    SiteDisruptionSource,
    SiteDisruptionType,
)


class SiteDisruptionCreate(BaseModel):
    activity_id: int | None = Field(default=None, gt=0)
    type: SiteDisruptionType
    severity: SiteDisruptionSeverity
    start_time: datetime
    end_time: datetime | None = None
    zone: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    description: str | None = None
    source: SiteDisruptionSource = SiteDisruptionSource.MANUAL

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time.tzinfo is None or self.start_time.utcoffset() is None:
            raise ValueError("start_time must be timezone-aware")
        if self.end_time is not None:
            if self.end_time.tzinfo is None or self.end_time.utcoffset() is None:
                raise ValueError("end_time must be timezone-aware")
            if self.end_time < self.start_time:
                raise ValueError("end_time must be greater than or equal to start_time")
        return self


class SiteDisruptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    activity_id: int | None
    type: SiteDisruptionType
    severity: SiteDisruptionSeverity
    start_time: datetime
    end_time: datetime | None
    duration_minutes: int | None
    zone: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    description: str | None
    source: SiteDisruptionSource
    created_by: int | None
    created_at: datetime


class SiteDisruptionListResponse(BaseModel):
    items: list[SiteDisruptionResponse]
    page: int
    page_size: int
    total: int


class ActiveDisruptionsResponse(BaseModel):
    active_disruptions: list[SiteDisruptionResponse]


class ActivityDisruptionsResponse(BaseModel):
    activity_id: int
    activity_name: str
    disruptions: list[SiteDisruptionResponse]


class DisruptionImpactResponse(BaseModel):
    disruption: dict[str, Any]
    affected_activity: dict[str, Any] | None
    progress_context: dict[str, Any]
    delay_context: dict[str, Any]


class DisruptionSummaryResponse(BaseModel):
    total_disruptions: int
    weather_disruptions: int
    total_interruption_minutes: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    most_affected_zones: list[dict[str, Any]]
