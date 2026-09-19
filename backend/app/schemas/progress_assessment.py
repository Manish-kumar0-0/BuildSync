from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.models.progress_assessment import ProgressAssessmentStatus


class ProgressAssessmentRequest(BaseModel):
    assessment_date: date


class ProgressAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    project_id: int
    schedule_activity_id: int
    evidence_id: int | None
    comparison_id: int | None
    assessment_date: date
    planned_progress: Decimal | None = Field(default=None, ge=0, le=100)
    reported_progress: Decimal | None = Field(default=None, ge=0, le=100)
    measured_progress: Decimal | None = Field(default=None, ge=0, le=100)
    ai_estimated_progress: Decimal | None = Field(default=None, ge=0, le=100)
    ai_confidence: Decimal | None = Field(default=None, ge=0, le=100)
    fused_progress: Decimal | None = Field(default=None, ge=0, le=100)
    variance_from_plan: Decimal | None
    variance_from_reported: Decimal | None
    assessment_status: ProgressAssessmentStatus
    assessed_at: datetime
    created_at: datetime
    updated_at: datetime


class ProgressAssessmentListResponse(BaseModel):
    items: list[ProgressAssessmentResponse]
    page: int
    page_size: int
    total: int
