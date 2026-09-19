from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai_analysis import AIAnalysisStatus


class AIAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    evidence_id: int
    analysis_status: AIAnalysisStatus
    provider: str | None
    model_name: str | None
    estimated_progress: Decimal | None = Field(default=None, ge=0, le=100)
    confidence_score: Decimal | None = Field(default=None, ge=0, le=100)
    detected_elements: list[dict[str, Any]] | None
    observations: str | None
    discrepancies: Any | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AIAnalysisStatusResponse(BaseModel):
    id: int
    evidence_id: int
    analysis_status: AIAnalysisStatus
