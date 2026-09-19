from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.activity_measured_progress import (
    ActivityMeasuredProgress,
    MeasuredProgressVerificationStatus,
)
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus
from app.models.user import User, UserRole
from app.schemas.activity_measured_progress import (
    MeasuredProgressCreate,
    MeasuredProgressResponse,
    MeasuredProgressVerification,
)
from app.services.progress.assessment_service import assess_activity_progress

router = APIRouter(tags=["measured progress"])

SUBMIT_ROLES = {UserRole.FIELD_ENGINEER, UserRole.SITE_ENGINEER}
VERIFY_ROLES = {
    UserRole.SITE_ENGINEER,
    UserRole.QA_QC_ENGINEER,
    UserRole.PROJECT_MANAGER,
    UserRole.ADMIN,
}
READ_ROLES = VERIFY_ROLES | SUBMIT_ROLES


def _activity(db: Session, activity_id: int) -> Activity:
    activity = db.scalar(
        select(Activity)
        .options(selectinload(Activity.assignments))
        .where(Activity.id == activity_id)
    )
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field activity not found")
    return activity


def _can_read(activity: Activity, user: User) -> bool:
    if user.role not in READ_ROLES:
        return False
    if user.role in {UserRole.SITE_ENGINEER, UserRole.QA_QC_ENGINEER, UserRole.PROJECT_MANAGER, UserRole.ADMIN}:
        return True
    return any(
        item.user_id == user.id and item.status == AssignmentStatus.ACTIVE
        for item in activity.assignments
    )


def _can_submit(activity: Activity, user: User) -> bool:
    if user.role == UserRole.SITE_ENGINEER:
        return True
    return user.role == UserRole.FIELD_ENGINEER and any(
        item.user_id == user.id and item.status == AssignmentStatus.ACTIVE
        for item in activity.assignments
    )


def _ensure_read(activity: Activity, user: User) -> None:
    if not _can_read(activity, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")


@router.post(
    "/api/activities/{activity_id}/measured-progress",
    response_model=MeasuredProgressResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_measured_progress(
    activity_id: int,
    payload: MeasuredProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityMeasuredProgress:
    activity = _activity(db, activity_id)
    if not _can_submit(activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to submit measured progress")
    existing = db.scalar(
        select(ActivityMeasuredProgress).where(
            ActivityMeasuredProgress.activity_id == activity_id,
            ActivityMeasuredProgress.assessment_date == payload.assessment_date,
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Measured progress already exists for this activity and date",
        )
    record = ActivityMeasuredProgress(
        project_id=activity.project_id,
        activity_id=activity.id,
        assessment_date=payload.assessment_date,
        planned_quantity=payload.planned_quantity,
        completed_quantity=payload.completed_quantity,
        unit=payload.unit.strip(),
        notes=payload.notes,
        recorded_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/api/activities/{activity_id}/measured-progress",
    response_model=list[MeasuredProgressResponse],
)
def list_measured_progress(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActivityMeasuredProgress]:
    activity = _activity(db, activity_id)
    _ensure_read(activity, current_user)
    return list(
        db.scalars(
            select(ActivityMeasuredProgress)
            .where(ActivityMeasuredProgress.activity_id == activity_id)
            .order_by(ActivityMeasuredProgress.assessment_date.desc(), ActivityMeasuredProgress.id.desc())
        ).all()
    )


@router.post(
    "/api/measured-progress/{measured_progress_id}/verify",
    response_model=MeasuredProgressResponse,
)
def verify_measured_progress(
    measured_progress_id: int,
    payload: MeasuredProgressVerification,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityMeasuredProgress:
    record = db.scalar(
        select(ActivityMeasuredProgress)
        .options(selectinload(ActivityMeasuredProgress.activity).selectinload(Activity.assignments))
        .where(ActivityMeasuredProgress.id == measured_progress_id)
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Measured progress not found")
    if current_user.role not in VERIFY_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to verify measured progress")
    if record.recorded_by == current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Measured progress requires separation of duties")
    if payload.decision not in {
        MeasuredProgressVerificationStatus.VERIFIED,
        MeasuredProgressVerificationStatus.REJECTED,
    }:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Verification decision must be VERIFIED or REJECTED")
    record.verification_status = payload.decision
    record.verified_by = current_user.id
    record.verification_notes = payload.notes
    record.verified_at = datetime.now(timezone.utc)
    db.commit()
    if payload.decision == MeasuredProgressVerificationStatus.VERIFIED:
        assess_activity_progress(db, record.activity, record.assessment_date)
    db.refresh(record)
    return record
