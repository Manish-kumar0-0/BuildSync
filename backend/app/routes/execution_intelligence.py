from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.field_activity import Activity, AssignmentStatus
from app.models.user import User, UserRole
from app.schemas.execution_intelligence import ExecutionIntelligenceResponse
from app.services.execution_intelligence import build_execution_intelligence

router = APIRouter(tags=["execution intelligence"])

PROJECT_ROLES = {
    UserRole.ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
}
ASSIGNED_ROLES = {
    UserRole.FIELD_ENGINEER,
    UserRole.FOREMAN,
    UserRole.WORKER,
}


def _authorized(activity: Activity, user: User) -> bool:
    if user.role in PROJECT_ROLES:
        return True
    return user.role in ASSIGNED_ROLES and any(
        item.user_id == user.id and item.status == AssignmentStatus.ACTIVE
        for item in activity.assignments
    )


@router.get(
    "/api/activities/{activity_id}/execution-intelligence",
    response_model=ExecutionIntelligenceResponse,
)
def get_execution_intelligence(
    activity_id: int,
    assessment_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExecutionIntelligenceResponse:
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
    if not _authorized(activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    target_date = assessment_date or date.today()
    return build_execution_intelligence(db, activity, target_date)
