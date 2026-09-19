from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.risk_prediction import (
    PrimaryRisk,
    RiskLevel,
    RiskPredictionStatus,
)


class RiskPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    activity_id: int
    schedule_activity_id: int
    comparison_id: int | None
    prediction_date: date
    risk_level: RiskLevel
    risk_score: Decimal = Field(ge=0, le=100)
    predicted_delay_days: Decimal | None = Field(default=None, ge=0)
    confidence_score: Decimal = Field(ge=0, le=100)
    primary_risk: PrimaryRisk
    risk_factors: list[dict[str, Any]] | None
    explanation: str | None
    model_name: str | None
    model_version: str | None
    prediction_status: RiskPredictionStatus
    created_at: datetime
    updated_at: datetime


class RiskPredictionSummary(BaseModel):
    project_id: int
    activity_id: int
    latest_prediction_date: date | None
    risk_level: RiskLevel | None
    risk_score: Decimal | None = Field(default=None, ge=0, le=100)
    predicted_delay_days: Decimal | None = Field(default=None, ge=0)
    confidence_score: Decimal | None = Field(default=None, ge=0, le=100)
    primary_risk: PrimaryRisk | None
    prediction_status: RiskPredictionStatus | None


class RiskPredictionListResponse(BaseModel):
    items: list[RiskPredictionResponse]
    page: int
    page_size: int
    total: int
