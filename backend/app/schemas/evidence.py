from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.evidence import EvidenceStatus, EvidenceType
from app.models.evidence_verification import EvidenceVerificationDecision


class EvidenceUploaderResponse(BaseModel):
    id: int
    full_name: str
    role: str


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    activity_id: int
    evidence_type: EvidenceType
    file_name: str
    file_size: int
    mime_type: str
    latitude: Decimal | None
    longitude: Decimal | None
    gps_accuracy: Decimal | None
    captured_at: datetime | None
    uploaded_at: datetime
    reported_progress: Decimal | None
    notes: str | None
    status: EvidenceStatus
    uploaded_by: EvidenceUploaderResponse | None


class EvidenceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    evidence_type: EvidenceType
    reported_progress: Decimal | None
    captured_at: datetime | None
    uploaded_at: datetime
    status: EvidenceStatus
    uploaded_by: EvidenceUploaderResponse | None


class EvidenceUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    evidence_type: EvidenceType
    file_name: str
    reported_progress: Decimal | None
    latitude: Decimal | None
    longitude: Decimal | None
    gps_accuracy: Decimal | None
    captured_at: datetime | None
    status: EvidenceStatus


class EvidenceVerificationRequest(BaseModel):
    decision: EvidenceVerificationDecision
    comments: str | None = None


class VerificationUserResponse(BaseModel):
    id: int
    full_name: str
    role: str


class EvidenceVerificationResponse(BaseModel):
    evidence_id: int
    decision: EvidenceVerificationDecision
    status: EvidenceStatus
    comments: str | None
    verified_by: VerificationUserResponse
    verified_at: datetime


class EvidenceVerificationHistoryItem(BaseModel):
    decision: EvidenceVerificationDecision
    comments: str | None
    verified_by: VerificationUserResponse
    verified_at: datetime


class PendingEvidenceItem(BaseModel):
    evidence_id: int
    activity_id: int
    activity_name: str
    project_id: int
    project_name: str
    evidence_type: EvidenceType
    reported_progress: Decimal | None
    captured_at: datetime | None
    uploaded_by: EvidenceUploaderResponse | None
    status: EvidenceStatus
