from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


ChangeValue = Literal[
    "INCREASED",
    "DECREASED",
    "UNCHANGED",
    "REMOVED",
    "ADDED",
    "UNCLEAR",
]


class EvidenceComparisonRequest(BaseModel):
    previous_evidence_id: int | None = Field(default=None, gt=0)
    refresh_existing: bool = False


class VisionObservation(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    observation: str = Field(min_length=1, max_length=1000)
    change: ChangeValue
    confidence: float = Field(ge=0, le=1)


class VisionComparisonResult(BaseModel):
    comparison_status: Literal["COMPLETED"]
    overall_change: str = Field(min_length=1, max_length=50)
    confidence: float = Field(ge=0, le=1)
    observations: list[VisionObservation] = Field(default_factory=list)
    construction_change_score: float = Field(ge=0, le=1)
    absolute_progress_estimate: float | None = Field(default=None, ge=0, le=100)
    absolute_progress_confidence: float | None = Field(default=None, ge=0, le=100)
    possible_issues: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class EvidenceComparisonResponse(BaseModel):
    comparison_id: int
    current_evidence_id: int
    previous_evidence_id: int
    comparison_status: str
    overall_change: str
    confidence: Decimal
    construction_change_score: Decimal
    absolute_progress_estimate: Decimal | None
    absolute_progress_confidence: Decimal | None
    observations: list[dict]
    possible_issues: list[str]
    notes: str | None
    model: str
    created_at: datetime
    detections: dict[str, list[dict]] | None = None
    comparison: dict[str, list[dict]] | None = None
    opencv_difference: dict[str, float | int | str] | None = None
    gemini_explanation: str | None = None
    limitations: list[str] = Field(default_factory=list)
