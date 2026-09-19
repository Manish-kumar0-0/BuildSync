from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity, AssignmentStatus
from app.models.progress_assessment import (
    ProgressAssessment,
    ProgressAssessmentStatus,
)
from app.schemas.progress_assessment import (
    ProgressAssessmentListResponse,
    ProgressAssessmentRequest,
    ProgressAssessmentResponse,
)
from app.services.progress.assessment_service import assess_activity_progress
from app.models.construction_event import ConstructionEventType
from app.services.events.event_service import create_event

router = APIRouter(tags=["progress assessments"])

CREATE_ROLES = {UserRole.FIELD_ENGINEER, UserRole.SITE_ENGINEER, UserRole.ADMIN}
PROJECT_VIEW_ROLES = {
    UserRole.SITE_ENGINEER,
    UserRole.PROJECT_MANAGER,
    UserRole.ADMIN,
}
ASSIGNED_VIEW_ROLES = {
    UserRole.WORKER,
    UserRole.FOREMAN,
    UserRole.FIELD_ENGINEER,
}


def _activity_or_404(db: Session, activity_id: int) -> Activity:
    activity = db.scalar(
        select(Activity)
        .options(selectinload(Activity.assignments))
        .where(Activity.id == activity_id)
    )
    if activity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field activity not found")
    return activity


def _assigned(activity: Activity, user: User) -> bool:
    return any(
        assignment.user_id == user.id
        and assignment.status == AssignmentStatus.ACTIVE
        for assignment in activity.assignments
    )


def _can_view_activity(activity: Activity, user: User) -> bool:
    if user.role in PROJECT_VIEW_ROLES:
        return True
    return user.role in ASSIGNED_VIEW_ROLES and _assigned(activity, user)


def _can_create_activity_assessment(activity: Activity, user: User) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    return user.role in {
        UserRole.FIELD_ENGINEER,
        UserRole.SITE_ENGINEER,
    } and _assigned(activity, user)


def _ensure_project_view(user: User) -> None:
    if user.role not in PROJECT_VIEW_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Project assessment access is restricted to Site Engineers, Project Managers, and Admins",
        )


@router.post(
    "/api/activities/{activity_id}/progress-assessment",
    response_model=ProgressAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_progress_assessment(
    activity_id: int,
    data: ProgressAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressAssessment:
    activity = _activity_or_404(db, activity_id)
    if not _can_create_activity_assessment(activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You must be an assigned Field Engineer or Site Engineer to create an assessment",
        )
    assessment = assess_activity_progress(db, activity, data.assessment_date)
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.PROGRESS_ASSESSED,
        actor_user_id=current_user.id,
        event_timestamp=assessment.assessed_at,
        title="Progress assessed",
        description=f"Progress assessment created for {activity.name}.",
        metadata={
            "assessment_id": assessment.id,
            "assessment_date": assessment.assessment_date.isoformat(),
            "fused_progress": str(assessment.fused_progress)
            if assessment.fused_progress is not None
            else None,
        },
        evidence_id=assessment.evidence_id,
        reference_type="progress_assessment",
        reference_id=assessment.id,
    )
    db.commit()
    return assessment


@router.get(
    "/api/activities/{activity_id}/progress-assessment/latest",
    response_model=ProgressAssessmentResponse,
)
def get_latest_progress_assessment(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressAssessment:
    activity = _activity_or_404(db, activity_id)
    if not _can_view_activity(activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this activity's assessments",
        )
    assessment = db.scalar(
        select(ProgressAssessment)
        .where(ProgressAssessment.activity_id == activity_id)
        .order_by(
            ProgressAssessment.assessed_at.desc(),
            ProgressAssessment.id.desc(),
        )
    )
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Progress assessment not found")
    return assessment


@router.get(
    "/api/activities/{activity_id}/progress-assessments",
    response_model=ProgressAssessmentListResponse,
)
def list_activity_progress_assessments(
    activity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity = _activity_or_404(db, activity_id)
    if not _can_view_activity(activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this activity's assessments",
        )
    base_query = select(ProgressAssessment).where(
        ProgressAssessment.activity_id == activity_id
    )
    total = db.scalar(
        select(func.count()).select_from(
            base_query.order_by(None).subquery()
        )
    ) or 0
    items = list(
        db.scalars(
            base_query.order_by(
                ProgressAssessment.assessed_at.desc(),
                ProgressAssessment.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get(
    "/api/projects/{project_id}/progress-assessments",
    response_model=ProgressAssessmentListResponse,
)
def list_project_progress_assessments(
    project_id: int,
    assessment_status: ProgressAssessmentStatus | None = Query(
        None, alias="status"
    ),
    assessment_date: date | None = Query(None, alias="date"),
    activity_id: int | None = Query(None, gt=0),
    wbs_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    _ensure_project_view(current_user)
    base_query = (
        select(ProgressAssessment)
        .join(Activity, Activity.id == ProgressAssessment.activity_id)
        .where(ProgressAssessment.project_id == project_id)
    )
    if assessment_status is not None:
        base_query = base_query.where(
            ProgressAssessment.assessment_status == assessment_status
        )
    if assessment_date is not None:
        base_query = base_query.where(
            ProgressAssessment.assessment_date == assessment_date
        )
    if activity_id is not None:
        base_query = base_query.where(ProgressAssessment.activity_id == activity_id)
    if wbs_id is not None:
        base_query = base_query.where(Activity.wbs_id == wbs_id)

    total = db.scalar(
        select(func.count()).select_from(base_query.order_by(None).subquery())
    ) or 0
    items = list(
        db.scalars(
            base_query.order_by(
                ProgressAssessment.assessed_at.desc(),
                ProgressAssessment.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}
