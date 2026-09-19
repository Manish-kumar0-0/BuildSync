from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models.evidence import EvidenceStatus, EvidenceType


class EvidenceHistoryItem(BaseModel):
    evidence_id: int
    captured_at: datetime
    progress_reported: Decimal | None
    progress_ai_estimated: Decimal | None
    verification_status: EvidenceStatus
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    gps_accuracy: Decimal | None = None
    file_type: EvidenceType
    mime_type: str
    uploaded_by: str | None = None
    zone: str | None = None


class EvidenceHistoryResponse(BaseModel):
    activity_id: int
    activity_name: str
    history: list[EvidenceHistoryItem]


class EvidenceComparisonRecord(BaseModel):
    evidence_id: int
    captured_at: datetime
    progress_reported: Decimal | None
    progress_ai_estimated: Decimal | None
    verification_status: EvidenceStatus


class EvidenceComparisonResponse(BaseModel):
    current: EvidenceComparisonRecord
    previous: EvidenceComparisonRecord | None
    comparison_status: str
    time_difference_hours: float | None = None
    progress_change: Decimal | None = None
    reported_progress_change: Decimal | None = None
    ai_progress_change: Decimal | None = None
    location: dict[str, Any]


class DailyEvidenceSummaryResponse(BaseModel):
    project_id: int
    date: str
    total_evidence: int
    verified: int
    pending: int
    rejected: int
    activities_with_evidence: int


class VisionComparisonPlaceholder(BaseModel):
    status: str
    message: str
