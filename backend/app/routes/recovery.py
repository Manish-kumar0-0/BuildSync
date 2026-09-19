from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import User, UserRole
from app.models.field_activity import Activity, AssignmentStatus
from app.models.recovery import (
    RecommendationPriority,
    RecommendationStatus,
    RecommendationType,
    RecoveryRecommendation,
)
from app.models.risk_prediction import ActivityRiskPrediction
from app.schemas.recovery import (
    RecoveryRecommendationGenerateResponse,
    RecoveryRecommendationListResponse,
    RecoveryRecommendationResponse,
    RecoveryRecommendationStatusUpdate,
)
from app.services.recovery.recovery_engine import generate_recovery_recommendations
from app.services.notifications.notification_service import (
    notify_recovery_recommendation,
    notify_recovery_status,
)
from app.models.construction_event import ConstructionEventType
from app.services.events.event_service import create_event

router = APIRouter(tags=["recovery recommendations"])
MANAGEMENT_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
ACTIVITY_VIEW_ROLES = {
    UserRole.SITE_ENGINEER,
    UserRole.FIELD_ENGINEER,
    UserRole.WORKER,
    UserRole.FOREMAN,
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


def _can_view(activity: Activity, user: User) -> bool:
    return user.role in MANAGEMENT_ROLES or (
        user.role in ACTIVITY_VIEW_ROLES and _assigned(activity, user)
    )


def _can_manage(activity: Activity, user: User) -> bool:
    return user.role in MANAGEMENT_ROLES or (
        user.role == UserRole.SITE_ENGINEER and _assigned(activity, user)
    )


def _latest_risk(db: Session, activity_id: int) -> ActivityRiskPrediction | None:
    return db.scalar(
        select(ActivityRiskPrediction)
        .where(ActivityRiskPrediction.activity_id == activity_id)
        .order_by(
            ActivityRiskPrediction.prediction_date.desc(),
            ActivityRiskPrediction.id.desc(),
        )
    )


@router.post(
    "/api/activities/{activity_id}/recovery-recommendations",
    response_model=RecoveryRecommendationGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recovery_recommendations(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity = _activity_or_404(db, activity_id)
    if not _can_manage(activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only Project Managers, Admins, or assigned Site Engineers can generate recommendations",
        )
    risk_prediction = _latest_risk(db, activity_id)
    if risk_prediction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Risk prediction not found")
    recommendations = generate_recovery_recommendations(db, activity, risk_prediction)
    for recommendation in recommendations:
        notify_recovery_recommendation(db, recommendation, activity)
        create_event(
            db,
            project_id=activity.project_id,
            activity_id=activity.id,
            wbs_id=activity.wbs_id,
            event_type=ConstructionEventType.RECOVERY_RECOMMENDED,
            actor_user_id=current_user.id,
            title="Recovery recommendation created",
            description=recommendation.description,
            metadata={
                "recommendation_type": recommendation.recommendation_type.value,
                "priority": recommendation.priority.value,
            },
            reference_type="recovery_recommendation",
            reference_id=recommendation.id,
        )
    db.commit()
    return {
        "activity_id": activity.id,
        "risk_level": risk_prediction.risk_level,
        "predicted_delay_days": risk_prediction.predicted_delay_days,
        "recommendations": recommendations,
    }


@router.get(
    "/api/activities/{activity_id}/recovery-recommendations",
    response_model=RecoveryRecommendationListResponse,
)
def list_recovery_recommendations(
    activity_id: int,
    recommendation_status: RecommendationStatus | None = Query(None, alias="status"),
    priority: RecommendationPriority | None = None,
    recommendation_type: RecommendationType | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity = _activity_or_404(db, activity_id)
    if not _can_view(activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to view recommendations")
    query = select(RecoveryRecommendation).where(
        RecoveryRecommendation.activity_id == activity_id
    )
    if recommendation_status is not None:
        query = query.where(RecoveryRecommendation.status == recommendation_status)
    if priority is not None:
        query = query.where(RecoveryRecommendation.priority == priority)
    if recommendation_type is not None:
        query = query.where(
            RecoveryRecommendation.recommendation_type == recommendation_type
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(RecoveryRecommendation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.patch(
    "/api/recovery-recommendations/{recommendation_id}",
    response_model=RecoveryRecommendationResponse,
)
def update_recovery_recommendation(
    recommendation_id: int,
    data: RecoveryRecommendationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecoveryRecommendation:
    recommendation = db.scalar(
        select(RecoveryRecommendation)
        .options(selectinload(RecoveryRecommendation.activity))
        .where(RecoveryRecommendation.id == recommendation_id)
    )
    if recommendation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recovery recommendation not found")
    if not _can_manage(recommendation.activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to update recommendations")
    allowed = {
        RecommendationStatus.SUGGESTED: {RecommendationStatus.ACCEPTED, RecommendationStatus.REJECTED},
        RecommendationStatus.ACCEPTED: {RecommendationStatus.IMPLEMENTED},
    }
    if data.status not in allowed.get(recommendation.status, set()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid status transition from {recommendation.status.value} to {data.status.value}",
        )
    recommendation.status = data.status
    db.commit()
    db.refresh(recommendation)
    if data.status == RecommendationStatus.ACCEPTED:
        notify_recovery_status(db, recommendation, recommendation.activity)
    create_event(
        db,
        project_id=recommendation.project_id,
        activity_id=recommendation.activity_id,
        wbs_id=recommendation.activity.wbs_id,
        event_type=(
            ConstructionEventType.RECOVERY_ACCEPTED
            if data.status == RecommendationStatus.ACCEPTED
            else ConstructionEventType.RECOVERY_IMPLEMENTED
        ),
        actor_user_id=current_user.id,
        title=f"Recovery recommendation {data.status.value.lower()}",
        description=recommendation.description,
        metadata={"status": data.status.value},
        reference_type="recovery_recommendation_status",
        reference_id=recommendation.id,
    )
    db.commit()
    return recommendation
