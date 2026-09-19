from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity, AssignmentStatus
from app.models.risk_prediction import (
    ActivityRiskPrediction,
    PrimaryRisk,
    RiskLevel,
)
from app.schemas.progress_assessment import ProgressAssessmentRequest
from app.schemas.risk_prediction import (
    RiskPredictionListResponse,
    RiskPredictionResponse,
)
from app.services.risk.risk_engine import calculate_activity_risk
from app.services.notifications.notification_service import notify_risk_prediction
from app.models.construction_event import ConstructionEventType
from app.services.events.event_service import create_event

router = APIRouter(tags=["risk predictions"])
PROJECT_RISK_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
RELEVANT_ACTIVITY_ROLES = {
    UserRole.SITE_ENGINEER,
    UserRole.FIELD_ENGINEER,
    UserRole.WORKER,
    UserRole.FOREMAN,
}


def _activity_or_404(db: Session, activity_id: int) -> Activity:
    activity = db.scalar(
        select(Activity)
        .options(
            selectinload(Activity.assignments),
            selectinload(Activity.schedule_activity),
        )
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


def _can_generate(activity: Activity, user: User) -> bool:
    if user.role in PROJECT_RISK_ROLES:
        return True
    return user.role == UserRole.SITE_ENGINEER and _assigned(activity, user)


def _can_view_activity(activity: Activity, user: User) -> bool:
    if user.role in PROJECT_RISK_ROLES:
        return True
    return user.role in RELEVANT_ACTIVITY_ROLES and _assigned(activity, user)


@router.post(
    "/api/activities/{activity_id}/risk-prediction",
    response_model=RiskPredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_prediction(
    activity_id: int,
    data: ProgressAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityRiskPrediction:
    activity = _activity_or_404(db, activity_id)
    if not _can_generate(activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only Project Managers, Admins, or assigned Site Engineers can generate risk predictions",
        )
    prediction = calculate_activity_risk(db, activity, data.assessment_date)
    notify_risk_prediction(db, prediction, activity, data.assessment_date)
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.RISK_DETECTED,
        actor_user_id=current_user.id,
        title="Risk detected",
        description=prediction.explanation,
        metadata={
            "risk_level": prediction.risk_level.value,
            "risk_score": str(prediction.risk_score),
            "primary_risk": prediction.primary_risk.value,
        },
        reference_type="risk_prediction",
        reference_id=prediction.id,
    )
    if prediction.predicted_delay_days is not None:
        create_event(
            db,
            project_id=activity.project_id,
            activity_id=activity.id,
            wbs_id=activity.wbs_id,
            event_type=ConstructionEventType.DELAY_PREDICTED,
            actor_user_id=current_user.id,
            title="Delay predicted",
            description=f"Predicted delay for {activity.name}.",
            metadata={"predicted_delay_days": str(prediction.predicted_delay_days)},
            reference_type="risk_prediction_delay",
            reference_id=prediction.id,
        )
    db.commit()
    return prediction


@router.get(
    "/api/activities/{activity_id}/risk-prediction/latest",
    response_model=RiskPredictionResponse,
)
def get_latest_risk_prediction(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityRiskPrediction:
    activity = _activity_or_404(db, activity_id)
    if not _can_view_activity(activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this activity's risk prediction",
        )
    prediction = db.scalar(
        select(ActivityRiskPrediction)
        .where(ActivityRiskPrediction.activity_id == activity_id)
        .order_by(
            ActivityRiskPrediction.prediction_date.desc(),
            ActivityRiskPrediction.id.desc(),
        )
    )
    if prediction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Risk prediction not found")
    return prediction


@router.get(
    "/api/projects/{project_id}/risk-predictions",
    response_model=RiskPredictionListResponse,
)
def list_project_risk_predictions(
    project_id: int,
    risk_level: RiskLevel | None = None,
    primary_risk: PrimaryRisk | None = None,
    prediction_date: date | None = Query(None, alias="date"),
    activity_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if current_user.role not in PROJECT_RISK_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Project risk access is restricted to Project Managers and Admins",
        )
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    base_query = select(ActivityRiskPrediction).where(
        ActivityRiskPrediction.project_id == project_id
    )
    if risk_level is not None:
        base_query = base_query.where(ActivityRiskPrediction.risk_level == risk_level)
    if primary_risk is not None:
        base_query = base_query.where(
            ActivityRiskPrediction.primary_risk == primary_risk
        )
    if prediction_date is not None:
        base_query = base_query.where(
            ActivityRiskPrediction.prediction_date == prediction_date
        )
    if activity_id is not None:
        base_query = base_query.where(
            ActivityRiskPrediction.activity_id == activity_id
        )
    total = db.scalar(
        select(func.count()).select_from(base_query.order_by(None).subquery())
    ) or 0
    items = list(
        db.scalars(
            base_query.order_by(
                ActivityRiskPrediction.prediction_date.desc(),
                ActivityRiskPrediction.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}
