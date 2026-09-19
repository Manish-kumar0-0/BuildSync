import math
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Evidence, Project, User, UserRole
from app.models.ai_analysis import AIAnalysisStatus
from app.models.evidence import EvidenceStatus
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus
from app.schemas.evidence_comparison import (
    DailyEvidenceSummaryResponse,
    EvidenceComparisonRecord,
    EvidenceComparisonResponse,
    EvidenceHistoryItem,
    EvidenceHistoryResponse,
)
from app.routes.evidence import _can_view_activity
from app.routes.events import _activity, _assigned_activity_ids

router = APIRouter(tags=["evidence comparison"])
MANAGEMENT_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
VALID_STATUSES = {
    EvidenceStatus.UPLOADED,
    EvidenceStatus.PROCESSING,
    EvidenceStatus.ANALYZED,
    EvidenceStatus.VERIFICATION_PENDING,
    EvidenceStatus.VERIFIED,
}


def _captured_at(evidence: Evidence) -> datetime:
    return evidence.captured_at or evidence.uploaded_at


def _is_valid_comparison_order(previous: Evidence, current: Evidence) -> bool:
    previous_timestamp = _captured_at(previous)
    current_timestamp = _captured_at(current)
    if previous_timestamp < current_timestamp:
        return True
    if previous_timestamp == current_timestamp:
        # Evidence ID is only a deterministic tie-breaker for an exact timestamp collision.
        return previous.id < current.id
    return False


def _load_evidence(db: Session, evidence_id: int) -> Evidence:
    evidence = db.scalar(
        select(Evidence)
        .options(
            selectinload(Evidence.activity),
            selectinload(Evidence.uploader),
            selectinload(Evidence.ai_analyses),
        )
        .where(Evidence.id == evidence_id)
    )
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    return evidence


def _ensure_activity_access(db: Session, activity: Activity, user: User) -> None:
    if not _can_view_activity(db, activity, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to view this evidence")


def _latest_ai_estimate(evidence: Evidence) -> Decimal | None:
    for analysis in sorted(
        evidence.ai_analyses, key=lambda item: (item.created_at, item.id), reverse=True
    ):
        if analysis.analysis_status == AIAnalysisStatus.COMPLETED:
            return analysis.estimated_progress
    return None


def _record(evidence: Evidence) -> EvidenceComparisonRecord:
    return EvidenceComparisonRecord(
        evidence_id=evidence.id,
        captured_at=_captured_at(evidence),
        progress_reported=evidence.reported_progress,
        progress_ai_estimated=_latest_ai_estimate(evidence),
        verification_status=evidence.status,
    )


def _history_item(evidence: Evidence) -> EvidenceHistoryItem:
    return EvidenceHistoryItem(
        evidence_id=evidence.id,
        captured_at=_captured_at(evidence),
        progress_reported=evidence.reported_progress,
        progress_ai_estimated=_latest_ai_estimate(evidence),
        verification_status=evidence.status,
        latitude=evidence.latitude,
        longitude=evidence.longitude,
        gps_accuracy=evidence.gps_accuracy,
        file_type=evidence.evidence_type,
        mime_type=evidence.mime_type,
        uploaded_by=evidence.uploader.full_name if evidence.uploader else None,
        zone=evidence.activity.zone if evidence.activity else None,
    )


def _previous(
    db: Session, current: Evidence, previous_id: int | None = None
) -> Evidence | None:
    if previous_id is not None:
        previous = _load_evidence(db, previous_id)
        if (
            previous.project_id != current.project_id
            or previous.activity_id != current.activity_id
            or previous.status not in VALID_STATUSES
        ):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Evidence records must belong to the same activity and be valid")
        if not _is_valid_comparison_order(previous, current):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Previous evidence must precede current evidence")
        return previous
    current_time = _captured_at(current)
    return db.scalar(
        select(Evidence)
        .options(
            selectinload(Evidence.ai_analyses),
            selectinload(Evidence.uploader),
            selectinload(Evidence.activity),
        )
        .where(
            Evidence.project_id == current.project_id,
            Evidence.activity_id == current.activity_id,
            Evidence.status.in_(VALID_STATUSES),
            or_(
                func.coalesce(Evidence.captured_at, Evidence.uploaded_at) < current_time,
                (
                    func.coalesce(Evidence.captured_at, Evidence.uploaded_at) == current_time
                )
                & (Evidence.id < current.id),
            ),
            Evidence.id != current.id,
        )
        .order_by(Evidence.captured_at.desc(), Evidence.uploaded_at.desc(), Evidence.id.desc())
        .limit(1)
    )


def _distance_meters(current: Evidence, previous: Evidence) -> float | None:
    if None in (
        current.latitude,
        current.longitude,
        previous.latitude,
        previous.longitude,
    ):
        return None
    radius = 6_371_000
    lat1, lat2 = math.radians(float(current.latitude)), math.radians(float(previous.latitude))
    delta_lat = lat2 - lat1
    delta_lon = math.radians(float(previous.longitude) - float(current.longitude))
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _comparison(
    current: Evidence, previous: Evidence | None
) -> EvidenceComparisonResponse:
    current_record = _record(current)
    if previous is None:
        return EvidenceComparisonResponse(
            current=current_record,
            previous=None,
            comparison_status="NO_PREVIOUS_EVIDENCE",
            location={"same_zone": None, "distance_meters": None},
        )
    reported_change = (
        current.reported_progress - previous.reported_progress
        if current.reported_progress is not None and previous.reported_progress is not None
        else None
    )
    current_ai = _latest_ai_estimate(current)
    previous_ai = _latest_ai_estimate(previous)
    ai_change = current_ai - previous_ai if current_ai is not None and previous_ai is not None else None
    time_hours = (_captured_at(current) - _captured_at(previous)).total_seconds() / 3600
    status_value = (
        "COMPARABLE"
        if reported_change is not None or ai_change is not None
        else "INSUFFICIENT_DATA"
    )
    return EvidenceComparisonResponse(
        current=current_record,
        previous=_record(previous),
        comparison_status=status_value,
        time_difference_hours=time_hours,
        progress_change=reported_change,
        reported_progress_change=reported_change,
        ai_progress_change=ai_change,
        location={
            "same_zone": current.activity.zone == previous.activity.zone,
            "distance_meters": _distance_meters(current, previous),
        },
    )


@router.get(
    "/api/activities/{activity_id}/evidence-history",
    response_model=EvidenceHistoryResponse,
)
def evidence_history(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceHistoryResponse:
    activity = _activity(db, activity_id)
    _ensure_activity_access(db, activity, current_user)
    evidence = db.scalars(
        select(Evidence)
        .options(
            selectinload(Evidence.ai_analyses),
            selectinload(Evidence.uploader),
            selectinload(Evidence.activity),
        )
        .where(Evidence.activity_id == activity_id)
        .order_by(func.coalesce(Evidence.captured_at, Evidence.uploaded_at).asc(), Evidence.id.asc())
    ).all()
    return EvidenceHistoryResponse(
        activity_id=activity.id,
        activity_name=activity.name,
        history=[_history_item(item) for item in evidence],
    )


@router.get("/api/activities/{activity_id}/evidence/latest", response_model=EvidenceComparisonRecord)
def latest_evidence(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceComparisonRecord:
    activity = _activity(db, activity_id)
    _ensure_activity_access(db, activity, current_user)
    evidence = db.scalar(
        select(Evidence)
        .options(selectinload(Evidence.ai_analyses))
        .where(
            Evidence.activity_id == activity_id,
            Evidence.status.in_(VALID_STATUSES),
        )
        .order_by(func.coalesce(Evidence.captured_at, Evidence.uploaded_at).desc(), Evidence.id.desc())
    )
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No valid evidence found for this activity")
    return _record(evidence)


def _comparison_for_id(
    db: Session, evidence_id: int, current_user: User, previous_id: int | None = None
) -> EvidenceComparisonResponse:
    current = _load_evidence(db, evidence_id)
    _ensure_activity_access(db, current.activity, current_user)
    if current.status not in VALID_STATUSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Evidence is not valid for comparison")
    previous = _previous(db, current, previous_id)
    if previous is not None:
        _ensure_activity_access(db, previous.activity, current_user)
    return _comparison(current, previous)


@router.get("/api/evidence/{evidence_id}/previous", response_model=EvidenceComparisonResponse)
def previous_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceComparisonResponse:
    return _comparison_for_id(db, evidence_id, current_user)


@router.get("/api/evidence/{evidence_id}/comparison", response_model=EvidenceComparisonResponse)
def evidence_comparison(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceComparisonResponse:
    return _comparison_for_id(db, evidence_id, current_user)


@router.get("/api/activities/{activity_id}/evidence/compare", response_model=EvidenceComparisonResponse)
def compare_activity_evidence(
    activity_id: int,
    current_evidence_id: int = Query(..., gt=0),
    previous_evidence_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceComparisonResponse:
    activity = _activity(db, activity_id)
    _ensure_activity_access(db, activity, current_user)
    current = _load_evidence(db, current_evidence_id)
    if current.activity_id != activity.id or current.project_id != activity.project_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Current evidence does not belong to this activity")
    return _comparison_for_id(db, current.id, current_user, previous_evidence_id)


@router.get(
    "/api/projects/{project_id}/evidence/daily-summary",
    response_model=DailyEvidenceSummaryResponse,
)
def daily_evidence_summary(
    project_id: int,
    date_value: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyEvidenceSummaryResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    query = (
        select(Evidence)
        .join(Activity, Activity.id == Evidence.activity_id)
        .where(Evidence.project_id == project_id)
    )
    if current_user.role not in MANAGEMENT_ROLES:
        if current_user.role == UserRole.SITE_ENGINEER:
            if not _assigned_activity_ids(db, current_user.id, project_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project evidence")
        else:
            query = query.join(
                ActivityAssignment,
                ActivityAssignment.activity_id == Activity.id,
            ).where(
                ActivityAssignment.user_id == current_user.id,
                ActivityAssignment.status == AssignmentStatus.ACTIVE,
            )
    if date_value is None:
        date_value = datetime.now(timezone.utc).date()
    start = datetime.combine(date_value, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    query = query.where(
        func.coalesce(Evidence.captured_at, Evidence.uploaded_at) >= start,
        func.coalesce(Evidence.captured_at, Evidence.uploaded_at) < end,
    )
    evidence = db.scalars(query).all()
    verified = sum(item.status == EvidenceStatus.VERIFIED for item in evidence)
    rejected = sum(item.status == EvidenceStatus.REJECTED for item in evidence)
    return DailyEvidenceSummaryResponse(
        project_id=project_id,
        date=date_value.isoformat(),
        total_evidence=len(evidence),
        verified=verified,
        pending=len(evidence) - verified - rejected,
        rejected=rejected,
        activities_with_evidence=len({item.activity_id for item in evidence}),
    )
