from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ExecutionIntelligenceResponse(BaseModel):
    activity_id: int
    assessment_date: date
    planned_start: date | None
    planned_end: date | None
    planned_progress: Decimal | None = Field(default=None, ge=0, le=100)
    actual_progress: Decimal | None = Field(default=None, ge=0, le=100)
    actual_progress_source: str
    actual_progress_confidence: Decimal | None = Field(default=None, ge=0, le=100)
    actual_progress_reason: str
    variance: Decimal | None
    variance_status: str
    assessment_id: int | None
    productivity_rate: Decimal | None
    productivity_observation_ids: list[int]
    productivity_source_assessment_ids: list[int]
    productivity_source_observation_ids: list[int]
    productivity_status: str
    productivity_reason: str
    predicted_delay_days: Decimal | None
    expected_completion_date: date | None
    delay_status: str
    delay_reason: str
    delay_source_assessment_id: int | None
    delay_source_assessment_ids: list[int]
    delay_source_observation_ids: list[int]
    risk_prediction_id: int | None
    recovery_recommendation_id: int | None
