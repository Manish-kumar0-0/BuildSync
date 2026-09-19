from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AIAnalysisRunResponse(BaseModel):
    evidence_id: int
    analysis_id: int
    status: str
    estimated_progress: Decimal | None = Field(default=None, ge=0, le=100)
    confidence_score: Decimal | None = Field(default=None, ge=0, le=100)
    detected_elements: list[dict[str, Any]] | None = None
    observations: list[str] | None = None
    discrepancies: list[Any] | None = None
