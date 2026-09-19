from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.recovery import (
    ImplementationEffort,
    RecommendationImpact,
    RecommendationPriority,
    RecommendationStatus,
    RecommendationType,
)
from app.models.risk_prediction import RiskLevel


class RecoveryRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    activity_id: int
    risk_prediction_id: int
    recommendation_type: RecommendationType
    priority: RecommendationPriority
    title: str
    description: str
    expected_impact: RecommendationImpact
    estimated_cost_impact: Decimal | None
    implementation_effort: ImplementationEffort
    status: RecommendationStatus
    created_at: datetime
    updated_at: datetime


class RecoveryRecommendationGenerateResponse(BaseModel):
    activity_id: int
    risk_level: RiskLevel
    predicted_delay_days: Decimal | None
    recommendations: list[RecoveryRecommendationResponse]


class RecoveryRecommendationListResponse(BaseModel):
    items: list[RecoveryRecommendationResponse]
    page: int
    page_size: int
    total: int


class RecoveryRecommendationStatusUpdate(BaseModel):
    status: RecommendationStatus
