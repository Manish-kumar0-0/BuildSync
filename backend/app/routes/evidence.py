import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.evidence import Evidence, EvidenceStatus, EvidenceType
from app.models.evidence_verification import (
    EvidenceVerification,
    EvidenceVerificationDecision,
)
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus
from app.models.ai_analysis import AIAnalysis, AIAnalysisStatus
from app.schemas.ai_analysis_run import AIAnalysisRunResponse
from app.services.ai.gemini_vision import GeminiVisionError
from app.services.ai.vision_service import VisionService
from app.services.notifications.notification_service import notify_evidence_event
from app.models.construction_event import ConstructionEventType
from app.services.events.event_service import create_event
from app.schemas.evidence import (
    EvidenceVerificationHistoryItem,
    EvidenceVerificationRequest,
    EvidenceVerificationResponse,
    EvidenceListItem,
    EvidenceResponse,
    EvidenceUploadResponse,
    PendingEvidenceItem,
    VerificationUserResponse,
)

router = APIRouter(tags=["evidence"])

ALLOWED_MIME_TYPES = {
    "image/jpeg": EvidenceType.PHOTO,
    "image/png": EvidenceType.PHOTO,
    "image/webp": EvidenceType.PHOTO,
    "video/mp4": EvidenceType.VIDEO,
    "application/pdf": EvidenceType.DOCUMENT,
}
UPLOAD_ROLES = {
    UserRole.WORKER,
    UserRole.FOREMAN,
    UserRole.FIELD_ENGINEER,
    UserRole.SITE_ENGINEER,
}
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _decimal(value: str | None, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        raise HTTPException(422, f"{field_name} must be a valid number") from None


def _validate_decimal_range(
    value: Decimal | None,
    field_name: str,
    minimum: Decimal,
    maximum: Decimal | None = None,
) -> None:
    if value is None:
        return
    if value < minimum or (maximum is not None and value > maximum):
        limit = f"{minimum} to {maximum}" if maximum is not None else f">= {minimum}"
        raise HTTPException(422, f"{field_name} must be {limit}")


def _safe_display_name(filename: str | None) -> str:
    name = Path(filename or "upload").name
    safe_name = FILENAME_PATTERN.sub("_", name).strip("._")
    return safe_name[:255] or "upload"


def _extension_for_mime(mime_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "application/pdf": ".pdf",
    }[mime_type]


def _parse_captured_at(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        captured_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, "captured_at must be a valid ISO 8601 timestamp") from None
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise HTTPException(422, "captured_at must be timezone-aware")
    return captured_at


def _activity_for_upload(db: Session, activity_id: int, user: User) -> Activity:
    activity = db.scalar(
        select(Activity)
        .options(selectinload(Activity.assignments))
        .where(Activity.id == activity_id)
    )
    if activity is None:
        raise HTTPException(404, "Field activity not found")
    if user.role not in UPLOAD_ROLES:
        raise HTTPException(403, "Your role is not allowed to upload evidence")
    if not any(
        assignment.user_id == user.id and assignment.status == AssignmentStatus.ACTIVE
        for assignment in activity.assignments
    ) and activity.responsible_user_id != user.id:
        raise HTTPException(403, "You must be assigned to this activity")
    return activity


PROJECT_VIEW_ROLES = {
    UserRole.FIELD_ENGINEER,
    UserRole.SITE_ENGINEER,
    UserRole.QA_QC_ENGINEER,
    UserRole.PROJECT_MANAGER,
    UserRole.ADMIN,
}
VERIFICATION_ROLES = {
    UserRole.SITE_ENGINEER,
    UserRole.FIELD_ENGINEER,
    UserRole.QA_QC_ENGINEER,
    UserRole.PROJECT_MANAGER,
    UserRole.ADMIN,
}


def _can_view_activity(db: Session, activity: Activity, user: User) -> bool:
    if user.role in PROJECT_VIEW_ROLES:
        return True
    return (
        db.scalar(
            select(ActivityAssignment.id).where(
                ActivityAssignment.activity_id == activity.id,
                ActivityAssignment.user_id == user.id,
                ActivityAssignment.status == AssignmentStatus.ACTIVE,
            )
        )
        is not None
    )


def _get_evidence_or_404(db: Session, evidence_id: int) -> Evidence:
    evidence = db.scalar(
        select(Evidence)
        .options(
            selectinload(Evidence.uploader),
            selectinload(Evidence.activity).selectinload(Activity.assignments),
        )
        .where(Evidence.id == evidence_id)
    )
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    return evidence


def _ensure_evidence_access(db: Session, evidence: Evidence, user: User) -> None:
    if not _can_view_activity(db, evidence.activity, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this evidence",
        )


def _evidence_filters(
    query,
    evidence_type: EvidenceType | None,
    evidence_status: EvidenceStatus | None,
    uploaded_by: int | None,
    evidence_date: date | None,
):
    if evidence_type is not None:
        query = query.where(Evidence.evidence_type == evidence_type)
    if evidence_status is not None:
        query = query.where(Evidence.status == evidence_status)
    if uploaded_by is not None:
        query = query.where(Evidence.uploaded_by == uploaded_by)
    if evidence_date is not None:
        query = query.where(func.date(Evidence.uploaded_at) == evidence_date)
    return query


def _safe_evidence_path(file_path: str) -> Path:
    root = UPLOAD_ROOT.resolve()
    candidate = (Path(__file__).resolve().parents[2] / file_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence file not found")
    return candidate


def _uploader_payload(evidence: Evidence) -> dict | None:
    if evidence.uploader is None:
        return None
    return {
        "id": evidence.uploader.id,
        "full_name": evidence.uploader.full_name,
        "role": evidence.uploader.role.value,
    }


def _evidence_response_payload(evidence: Evidence) -> dict:
    return {
        "id": evidence.id,
        "project_id": evidence.project_id,
        "activity_id": evidence.activity_id,
        "evidence_type": evidence.evidence_type,
        "file_name": evidence.file_name,
        "file_size": evidence.file_size,
        "mime_type": evidence.mime_type,
        "latitude": evidence.latitude,
        "longitude": evidence.longitude,
        "gps_accuracy": evidence.gps_accuracy,
        "captured_at": evidence.captured_at,
        "uploaded_at": evidence.uploaded_at,
        "reported_progress": evidence.reported_progress,
        "notes": evidence.notes,
        "status": evidence.status,
        "uploaded_by": _uploader_payload(evidence),
    }


def _evidence_list_item_payload(evidence: Evidence) -> dict:
    return {
        "id": evidence.id,
        "file_name": evidence.file_name,
        "evidence_type": evidence.evidence_type,
        "reported_progress": evidence.reported_progress,
        "captured_at": evidence.captured_at,
        "uploaded_at": evidence.uploaded_at,
        "status": evidence.status,
        "uploaded_by": _uploader_payload(evidence),
    }


def _can_verify_evidence(db: Session, evidence: Evidence, user: User) -> bool:
    return user.role in VERIFICATION_ROLES and _can_view_activity(db, evidence.activity, user)


def _analysis_response(analysis, evidence_id: int) -> dict:
    return {
        "evidence_id": evidence_id,
        "analysis_id": analysis.id,
        "status": analysis.analysis_status.value,
        "estimated_progress": analysis.estimated_progress,
        "confidence_score": analysis.confidence_score,
        "detected_elements": analysis.detected_elements,
        "observations": (
            analysis.observations.splitlines() if analysis.observations else None
        ),
        "discrepancies": analysis.discrepancies,
    }


@router.post(
    "/api/evidence/{evidence_id}/analyze",
    response_model=AIAnalysisRunResponse,
)
def analyze_evidence_endpoint(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    evidence = _get_evidence_or_404(db, evidence_id)
    if not _can_verify_evidence(db, evidence, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your role is not authorized to request evidence analysis",
        )
    if evidence.evidence_type != EvidenceType.PHOTO:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Only photo evidence is supported for analysis",
        )
    evidence_path = _safe_evidence_path(evidence.file_path)
    if not evidence_path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Evidence file not found",
        )
    activity = db.scalar(
        select(Activity)
        .options(
            selectinload(Activity.project),
            selectinload(Activity.schedule_activity),
            selectinload(Activity.wbs),
            selectinload(Activity.boq_item),
        )
        .where(Activity.id == evidence.activity_id)
    )
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field activity not found")

    try:
        analysis = VisionService().analyze_evidence(
            db,
            evidence,
            activity,
            activity.wbs,
            activity.boq_item,
        )
    except (GeminiVisionError, FileNotFoundError, ValueError):
        failed_analysis = db.scalar(
            select(AIAnalysis)
            .where(
                AIAnalysis.evidence_id == evidence.id,
                AIAnalysis.analysis_status == AIAnalysisStatus.FAILED,
            )
            .order_by(AIAnalysis.id.desc())
        )
        if failed_analysis is None:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Evidence analysis could not be completed",
            ) from None
        return _analysis_response(failed_analysis, evidence.id)

    evidence.status = EvidenceStatus.ANALYZED
    db.commit()
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.AI_ANALYSIS_COMPLETED,
        actor_user_id=current_user.id,
        title="AI analysis completed",
        description=f"AI analysis completed for evidence {evidence.id}.",
        metadata={
            "analysis_id": analysis.id,
            "confidence_score": str(analysis.confidence_score)
            if analysis.confidence_score is not None
            else None,
        },
        evidence_id=evidence.id,
        reference_type="ai_analysis",
        reference_id=analysis.id,
    )
    db.commit()
    return _analysis_response(analysis, evidence.id)


def _verification_user_payload(user: User) -> dict:
    return {"id": user.id, "full_name": user.full_name, "role": user.role.value}


def _verification_response_payload(
    verification: EvidenceVerification,
    evidence: Evidence,
    verifier: User,
) -> dict:
    return {
        "evidence_id": evidence.id,
        "decision": verification.decision,
        "status": evidence.status,
        "comments": verification.comments,
        "verified_by": _verification_user_payload(verifier),
        "verified_at": verification.verified_at,
    }


def _verification_history_payload(verification: EvidenceVerification) -> dict:
    return {
        "decision": verification.decision,
        "comments": verification.comments,
        "verified_by": _verification_user_payload(verification.verifier),
        "verified_at": verification.verified_at,
    }


@router.post(
    "/api/evidence/{evidence_id}/verify",
    response_model=EvidenceVerificationResponse,
)
def verify_evidence(
    evidence_id: int,
    data: EvidenceVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    evidence = _get_evidence_or_404(db, evidence_id)
    if not _can_verify_evidence(db, evidence, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your role is not authorized to verify evidence",
        )
    if evidence.status != EvidenceStatus.VERIFICATION_PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Evidence can only be verified while verification is pending",
        )
    comments = data.comments.strip() if data.comments else None
    if data.decision in {
        EvidenceVerificationDecision.REJECTED,
        EvidenceVerificationDecision.REQUEST_INFO,
    } and not comments:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Comments are required for rejection or additional information requests",
        )

    verification = EvidenceVerification(
        evidence_id=evidence.id,
        verified_by=current_user.id,
        decision=data.decision,
        comments=comments,
    )
    if data.decision == EvidenceVerificationDecision.APPROVED:
        evidence.status = EvidenceStatus.VERIFIED
    elif data.decision == EvidenceVerificationDecision.REJECTED:
        evidence.status = EvidenceStatus.REJECTED

    try:
        db.add(verification)
        db.commit()
        db.refresh(verification)
        db.refresh(evidence)
        if data.decision in {
            EvidenceVerificationDecision.APPROVED,
            EvidenceVerificationDecision.REJECTED,
        }:
            create_event(
                db,
                project_id=evidence.project_id,
                activity_id=evidence.activity_id,
                event_type=(
                    ConstructionEventType.EVIDENCE_VERIFIED
                    if data.decision == EvidenceVerificationDecision.APPROVED
                    else ConstructionEventType.EVIDENCE_REJECTED
                ),
                actor_user_id=current_user.id,
                title=(
                    "Evidence verified"
                    if data.decision == EvidenceVerificationDecision.APPROVED
                    else "Evidence rejected"
                ),
                description=comments,
                metadata={"decision": data.decision.value, "comments": comments},
                evidence_id=evidence.id,
                reference_type="evidence_verification",
                reference_id=verification.id,
            )
        if data.decision == EvidenceVerificationDecision.REJECTED:
            notify_evidence_event(db, evidence, evidence.activity, rejected=True)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Evidence verification could not be saved",
        ) from None

    return _verification_response_payload(verification, evidence, current_user)


@router.get(
    "/api/evidence/{evidence_id}/verifications",
    response_model=list[EvidenceVerificationHistoryItem],
)
def list_evidence_verifications(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    evidence = _get_evidence_or_404(db, evidence_id)
    _ensure_evidence_access(db, evidence, current_user)
    verifications = list(
        db.scalars(
            select(EvidenceVerification)
            .options(selectinload(EvidenceVerification.verifier))
            .where(EvidenceVerification.evidence_id == evidence_id)
            .order_by(
                EvidenceVerification.verified_at.desc(),
                EvidenceVerification.id.desc(),
            )
        ).all()
    )
    return [_verification_history_payload(item) for item in verifications]


@router.get(
    "/api/projects/{project_id}/evidence/pending-verification",
    response_model=list[PendingEvidenceItem],
)
def list_pending_verification(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    if current_user.role not in VERIFICATION_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your role is not authorized to review evidence",
        )
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    query = (
        select(Evidence, Activity, Project, User)
        .join(Activity, Evidence.activity_id == Activity.id)
        .join(Project, Evidence.project_id == Project.id)
        .outerjoin(User, Evidence.uploaded_by == User.id)
        .where(
            Evidence.project_id == project_id,
            Evidence.status == EvidenceStatus.VERIFICATION_PENDING,
        )
    )
    if current_user.role == UserRole.QA_QC_ENGINEER:
        query = query.join(
            ActivityAssignment,
            ActivityAssignment.activity_id == Activity.id,
        ).where(
            ActivityAssignment.user_id == current_user.id,
            ActivityAssignment.status == AssignmentStatus.ACTIVE,
        )
    query = query.order_by(Evidence.uploaded_at.desc(), Evidence.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    results = db.execute(query).unique().all()
    return [
        {
            "evidence_id": evidence.id,
            "activity_id": activity.id,
            "activity_name": activity.name,
            "project_id": project.id,
            "project_name": project.name,
            "evidence_type": evidence.evidence_type,
            "reported_progress": evidence.reported_progress,
            "captured_at": evidence.captured_at,
            "uploaded_by": (
                {
                    "id": uploader.id,
                    "full_name": uploader.full_name,
                    "role": uploader.role.value,
                }
                if uploader
                else None
            ),
            "status": evidence.status,
        }
        for evidence, activity, project, uploader in results
    ]


@router.get("/api/evidence/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    evidence = _get_evidence_or_404(db, evidence_id)
    _ensure_evidence_access(db, evidence, current_user)
    return _evidence_response_payload(evidence)


@router.get(
    "/api/activities/{activity_id}/evidence",
    response_model=list[EvidenceListItem],
)
def list_activity_evidence(
    activity_id: int,
    evidence_type: EvidenceType | None = Query(None),
    evidence_status: EvidenceStatus | None = Query(None, alias="status"),
    uploaded_by: int | None = Query(None, gt=0),
    evidence_date: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field activity not found")
    if not _can_view_activity(db, activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this activity's evidence",
        )
    query = (
        select(Evidence)
        .options(selectinload(Evidence.uploader))
        .where(Evidence.activity_id == activity_id)
    )
    query = _evidence_filters(
        query, evidence_type, evidence_status, uploaded_by, evidence_date
    )
    evidences = list(
        db.scalars(query.order_by(Evidence.uploaded_at.desc(), Evidence.id.desc())).all()
    )
    return [_evidence_list_item_payload(evidence) for evidence in evidences]


@router.get(
    "/api/projects/{project_id}/evidence",
    response_model=list[EvidenceListItem],
)
def list_project_evidence(
    project_id: int,
    activity_id: int | None = Query(None, gt=0),
    evidence_type: EvidenceType | None = Query(None),
    evidence_status: EvidenceStatus | None = Query(None, alias="status"),
    uploaded_by: int | None = Query(None, gt=0),
    evidence_date: date | None = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    if current_user.role not in PROJECT_VIEW_ROLES:
        has_project_access = db.scalar(
            select(ActivityAssignment.id)
            .join(Activity, ActivityAssignment.activity_id == Activity.id)
            .where(
                Activity.project_id == project_id,
                ActivityAssignment.user_id == current_user.id,
                ActivityAssignment.status == AssignmentStatus.ACTIVE,
            )
        )
        if has_project_access is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You are not authorized to view this project's evidence",
            )

    query = (
        select(Evidence)
        .join(Activity, Evidence.activity_id == Activity.id)
        .options(selectinload(Evidence.uploader))
        .where(Evidence.project_id == project_id)
    )
    if current_user.role not in PROJECT_VIEW_ROLES:
        query = query.join(
            ActivityAssignment,
            ActivityAssignment.activity_id == Activity.id,
        ).where(
            ActivityAssignment.user_id == current_user.id,
            ActivityAssignment.status == AssignmentStatus.ACTIVE,
        )
    if activity_id is not None:
        query = query.where(Evidence.activity_id == activity_id)
    query = _evidence_filters(
        query, evidence_type, evidence_status, uploaded_by, evidence_date
    )
    query = query.order_by(Evidence.uploaded_at.desc(), Evidence.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    evidences = list(db.scalars(query).unique().all())
    return [_evidence_list_item_payload(evidence) for evidence in evidences]


@router.get("/api/evidence/{evidence_id}/file")
def view_evidence_file(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evidence = _get_evidence_or_404(db, evidence_id)
    _ensure_evidence_access(db, evidence, current_user)
    file_path = _safe_evidence_path(evidence.file_path)
    if not file_path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence file not found")
    return FileResponse(
        path=file_path,
        media_type=evidence.mime_type,
        filename=evidence.file_name,
    )


@router.post(
    "/api/activities/{activity_id}/evidence",
    response_model=EvidenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_evidence(
    activity_id: int,
    file: UploadFile = File(...),
    latitude: str | None = Form(None),
    longitude: str | None = Form(None),
    gps_accuracy: str | None = Form(None),
    captured_at: str | None = Form(None),
    reported_progress: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Evidence:
    activity = _activity_for_upload(db, activity_id, current_user)
    mime_type = (file.content_type or "").lower()
    evidence_type = ALLOWED_MIME_TYPES.get(mime_type)
    if evidence_type is None:
        raise HTTPException(415, "Unsupported evidence file type")

    latitude_value = _decimal(latitude, "latitude")
    longitude_value = _decimal(longitude, "longitude")
    gps_accuracy_value = _decimal(gps_accuracy, "gps_accuracy")
    progress_value = _decimal(reported_progress, "reported_progress")
    _validate_decimal_range(latitude_value, "latitude", Decimal("-90"), Decimal("90"))
    _validate_decimal_range(longitude_value, "longitude", Decimal("-180"), Decimal("180"))
    _validate_decimal_range(gps_accuracy_value, "gps_accuracy", Decimal("0"))
    _validate_decimal_range(progress_value, "reported_progress", Decimal("0"), Decimal("100"))
    captured_at_value = _parse_captured_at(captured_at)

    safe_name = _safe_display_name(file.filename)
    relative_path = (
        Path("uploads")
        / str(activity.project_id)
        / str(activity.id)
        / date.today().isoformat()
        / f"{uuid.uuid4().hex}{_extension_for_mime(mime_type)}"
    )
    destination = UPLOAD_ROOT / relative_path.relative_to("uploads")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_size = 0
        with destination.open("xb") as output:
            while chunk := file.file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > settings.evidence_max_file_size_bytes:
                    raise HTTPException(413, "Evidence file is too large")
                output.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError:
        destination.unlink(missing_ok=True)
        raise HTTPException(500, "Evidence storage failed") from None

    evidence = Evidence(
        project_id=activity.project_id,
        activity_id=activity.id,
        uploaded_by=current_user.id,
        evidence_type=evidence_type,
        file_name=safe_name,
        file_path=relative_path.as_posix(),
        file_size=file_size,
        mime_type=mime_type,
        latitude=latitude_value,
        longitude=longitude_value,
        gps_accuracy=gps_accuracy_value,
        captured_at=captured_at_value,
        reported_progress=progress_value,
        notes=notes,
        status=EvidenceStatus.VERIFICATION_PENDING,
    )
    try:
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
    except SQLAlchemyError:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(500, "Evidence database creation failed") from None
    notify_evidence_event(db, evidence, activity, rejected=False)
    create_event(
        db,
        project_id=evidence.project_id,
        activity_id=evidence.activity_id,
        event_type=ConstructionEventType.EVIDENCE_CAPTURED,
        actor_user_id=current_user.id,
        event_timestamp=evidence.uploaded_at,
        latitude=evidence.latitude,
        longitude=evidence.longitude,
        gps_accuracy=evidence.gps_accuracy,
        zone=activity.zone,
        title="Evidence captured",
        description=evidence.notes,
        metadata={
            "evidence_type": evidence.evidence_type.value,
            "reported_progress": str(evidence.reported_progress)
            if evidence.reported_progress is not None
            else None,
        },
        evidence_id=evidence.id,
        reference_type="evidence",
        reference_id=evidence.id,
    )
    db.commit()
    return evidence
