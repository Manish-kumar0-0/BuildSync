from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.quality import (
    InspectionStatus, InspectionType, QualityDefectStatus, QualitySeverity,
)


class QualityInspectionCreate(BaseModel):
    activity_id: int | None = Field(default=None, gt=0)
    inspection_type: InspectionType
    status: InspectionStatus = InspectionStatus.PENDING
    score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    inspected_at: datetime

    @field_validator("inspected_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("inspected_at must include a timezone")
        return value


class QualityInspectionResponse(QualityInspectionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    inspector_id: int
    created_at: datetime

    @field_validator("inspected_at", mode="before")
    @classmethod
    def normalize_database_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class QualityDefectCreate(BaseModel):
    activity_id: int | None = Field(default=None, gt=0)
    inspection_id: int | None = Field(default=None, gt=0)
    severity: QualitySeverity
    description: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=255)


class QualityDefectResponse(QualityDefectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    status: QualityDefectStatus
    reported_by: int
    resolved_at: datetime | None
    created_at: datetime


class ActivityQualityResponse(BaseModel):
    latest_inspection: QualityInspectionResponse | None
    latest_score: int | None
    inspection_status: InspectionStatus | None
    open_defects: int
    critical_defects: int


class QualitySummary(BaseModel):
    project_id: int
    total_inspections: int
    passed: int
    failed: int
    conditional: int
    open_defects: int
    critical_defects: int
