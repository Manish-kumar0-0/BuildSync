from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import BOQItem, Project, ScheduleActivity, User, UserRole, WBS
from app.models.field_activity import (
    Activity,
    ActivityAssignment,
    AssignmentRole,
    AssignmentStatus,
    FieldActivityStatus,
)
from app.schemas.field_activity import (
    ActivityCreate,
    ActivityResponse,
    ActivitySummary,
    ActivityUpdate,
    AssignmentCreate,
    AssignmentResponse,
    ProgressUpdate,
)
from app.models.construction_event import ConstructionEventType
from app.services.events.event_service import create_event

router = APIRouter(tags=["field activities"])
MANAGERS = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
ASSIGNERS = MANAGERS | {UserRole.SITE_ENGINEER}
FIELD_USERS = {
    UserRole.WORKER,
    UserRole.FOREMAN,
    UserRole.FIELD_ENGINEER,
    UserRole.SITE_ENGINEER,
}


def get_or_404(db: Session, model: type, item_id: int, label: str):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, f"{label} not found")
    return item


def get_activity(db: Session, activity_id: int) -> Activity:
    activity = db.scalar(
        select(Activity)
        .options(selectinload(Activity.assignments))
        .where(Activity.id == activity_id)
    )
    if activity is None:
        raise HTTPException(404, "Field activity not found")
    return activity


def require_manager(user: User) -> None:
    if user.role not in MANAGERS:
        raise HTTPException(403, "Project Manager or Admin access is required")


def require_assigner(user: User) -> None:
    if user.role not in ASSIGNERS:
        raise HTTPException(403, "Assignment access is restricted to Site Engineers, Project Managers, and Admins")


def same_project(db: Session, model: type, item_id: int | None, project_id: int, label: str) -> None:
    if item_id is None:
        return
    item = get_or_404(db, model, item_id, label)
    if item.project_id != project_id:
        raise HTTPException(422, f"{label} must belong to the same project")


def commit(db: Session, item):
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def assigned_to(activity: Activity, user: User) -> bool:
    return any(
        assignment.user_id == user.id and assignment.status == AssignmentStatus.ACTIVE
        for assignment in activity.assignments
    )


def can_work(activity: Activity, user: User) -> None:
    if user.role in MANAGERS:
        return
    if user.role not in FIELD_USERS or not assigned_to(activity, user):
        raise HTTPException(403, "You must be assigned to this activity")


def transition_for_progress(activity: Activity, progress: Decimal) -> None:
    if activity.status in {
        FieldActivityStatus.SUBMITTED,
        FieldActivityStatus.AI_ANALYZED,
        FieldActivityStatus.VERIFIED,
        FieldActivityStatus.COMPLETED,
    }:
        raise HTTPException(409, "Progress cannot be changed after submission")
    if activity.status == FieldActivityStatus.NOT_STARTED and progress > 0:
        activity.status = FieldActivityStatus.STARTED
    elif activity.status == FieldActivityStatus.STARTED and progress > 0:
        activity.status = FieldActivityStatus.IN_PROGRESS


@router.post("/api/projects/{project_id}/activities", response_model=ActivityResponse, status_code=201)
def create_activity(
    project_id: int,
    data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_manager(current_user)
    get_or_404(db, Project, project_id, "Project")
    schedule = get_or_404(db, ScheduleActivity, data.schedule_activity_id, "Schedule activity")
    if schedule.project_id != project_id:
        raise HTTPException(422, "Schedule activity must belong to the same project")
    wbs_id = data.wbs_id if data.wbs_id is not None else schedule.wbs_id
    boq_item_id = data.boq_item_id if data.boq_item_id is not None else schedule.boq_item_id
    same_project(db, WBS, wbs_id, project_id, "WBS")
    same_project(db, BOQItem, boq_item_id, project_id, "BOQ item")
    activity = Activity(
        project_id=project_id,
        schedule_activity_id=schedule.id,
        wbs_id=wbs_id,
        boq_item_id=boq_item_id,
        activity_code=data.activity_code or schedule.activity_code,
        name=data.name or schedule.name,
        description=data.description or schedule.description,
        location=data.location,
        zone=data.zone,
        assigned_by=current_user.id,
    )
    activity = commit(db, activity)
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.ACTIVITY_CREATED,
        actor_user_id=current_user.id,
        title="Activity created",
        description=f"Activity {activity.name} was created.",
        reference_type="activity",
        reference_id=activity.id,
    )
    db.commit()
    return activity


@router.get("/api/projects/{project_id}/activities", response_model=list[ActivityResponse])
def list_project_activities(
    project_id: int,
    status_filter: FieldActivityStatus | None = Query(None, alias="status"),
    zone: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    get_or_404(db, Project, project_id, "Project")
    query = select(Activity).options(selectinload(Activity.assignments)).where(Activity.project_id == project_id)
    if status_filter:
        query = query.where(Activity.status == status_filter)
    if zone:
        query = query.where(Activity.zone == zone)
    return list(db.scalars(query.order_by(Activity.id)).all())


@router.get("/api/activities/{activity_id}", response_model=ActivityResponse)
def read_activity(activity_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_activity(db, activity_id)


@router.put("/api/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_manager(current_user)
    activity = get_activity(db, activity_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(activity, key, value)
    activity.last_updated_at = datetime.now(timezone.utc)
    return commit(db, activity)


@router.delete("/api/activities/{activity_id}", status_code=204)
def remove_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_manager(current_user)
    db.delete(get_activity(db, activity_id))
    db.commit()


@router.post("/api/activities/{activity_id}/assignments", response_model=AssignmentResponse, status_code=201)
def assign_activity(
    activity_id: int,
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_assigner(current_user)
    activity = get_activity(db, activity_id)
    user = get_or_404(db, User, data.user_id, "User")
    if not user.is_active:
        raise HTTPException(400, "Cannot assign an inactive user")
    if user.role not in {
        UserRole.WORKER,
        UserRole.FOREMAN,
        UserRole.FIELD_ENGINEER,
        UserRole.SITE_ENGINEER,
    }:
        raise HTTPException(422, "User role is not valid for field assignment")
    assignment = ActivityAssignment(
        activity_id=activity.id,
        user_id=user.id,
        assigned_by=current_user.id,
        assignment_role=data.assignment_role,
    )
    activity.responsible_user_id = user.id
    activity.assigned_by = current_user.id
    assignment = commit(db, assignment)
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.ACTIVITY_ASSIGNED,
        actor_user_id=current_user.id,
        title="Activity assigned",
        description=f"Activity {activity.name} was assigned.",
        metadata={"assigned_user_id": user.id, "assignment_role": data.assignment_role.value},
        reference_type="activity_assignment",
        reference_id=assignment.id,
    )
    db.commit()
    return assignment


@router.get("/api/activities/{activity_id}/assignments", response_model=list[AssignmentResponse])
def list_assignments(activity_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_activity(db, activity_id)
    return list(db.scalars(select(ActivityAssignment).where(ActivityAssignment.activity_id == activity_id)).all())


@router.delete("/api/activities/{activity_id}/assignments/{assignment_id}", status_code=204)
def remove_assignment(
    activity_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_assigner(current_user)
    get_activity(db, activity_id)
    assignment = db.scalar(
        select(ActivityAssignment).where(
            ActivityAssignment.id == assignment_id,
            ActivityAssignment.activity_id == activity_id,
        )
    )
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    assignment.status = AssignmentStatus.REMOVED
    db.commit()


@router.patch("/api/activities/{activity_id}/progress", response_model=ActivityResponse)
def update_progress(
    activity_id: int,
    data: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = get_activity(db, activity_id)
    can_work(activity, current_user)
    transition_for_progress(activity, data.progress_percentage)
    activity.progress_percentage = data.progress_percentage
    activity.last_updated_at = datetime.now(timezone.utc)
    activity = commit(db, activity)
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.PROGRESS_REPORTED,
        actor_user_id=current_user.id,
        title="Progress reported",
        description=f"Progress for {activity.name} updated.",
        metadata={"progress_percentage": str(activity.progress_percentage)},
        reference_type=f"activity_progress:{activity.progress_percentage}",
        reference_id=activity.id,
    )
    db.commit()
    return activity


@router.post("/api/activities/{activity_id}/start", response_model=ActivityResponse)
def start_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = get_activity(db, activity_id)
    can_work(activity, current_user)
    if activity.status != FieldActivityStatus.NOT_STARTED:
        raise HTTPException(409, "Only NOT_STARTED activities can be started")
    activity.status = FieldActivityStatus.STARTED
    activity.started_at = datetime.now(timezone.utc)
    activity.responsible_user_id = current_user.id
    activity.last_updated_at = datetime.now(timezone.utc)
    activity = commit(db, activity)
    create_event(
        db,
        project_id=activity.project_id,
        activity_id=activity.id,
        wbs_id=activity.wbs_id,
        event_type=ConstructionEventType.WORK_START,
        actor_user_id=current_user.id,
        event_timestamp=activity.started_at,
        title="Work started",
        description=f"Work started for {activity.name}.",
        reference_type="activity_start",
        reference_id=activity.id,
    )
    db.commit()
    return activity


@router.post("/api/activities/{activity_id}/submit", response_model=ActivityResponse)
def submit_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = get_activity(db, activity_id)
    can_work(activity, current_user)
    if activity.status != FieldActivityStatus.IN_PROGRESS:
        raise HTTPException(409, "Only IN_PROGRESS activities can be submitted")
    activity.status = FieldActivityStatus.SUBMITTED
    activity.last_updated_at = datetime.now(timezone.utc)
    return commit(db, activity)


@router.get("/api/users/me/activities", response_model=list[ActivityResponse])
def my_activities(
    status_filter: FieldActivityStatus | None = Query(None, alias="status"),
    project_id: int | None = Query(None, gt=0),
    date_filter: str | None = Query(None, alias="date"),
    zone: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Activity)
        .join(ActivityAssignment)
        .options(selectinload(Activity.assignments))
        .where(
            ActivityAssignment.user_id == current_user.id,
            ActivityAssignment.status == AssignmentStatus.ACTIVE,
        )
    )
    if status_filter:
        query = query.where(Activity.status == status_filter)
    if project_id:
        query = query.where(Activity.project_id == project_id)
    if date_filter:
        query = query.where(func.date(Activity.created_at) == date_filter)
    if zone:
        query = query.where(Activity.zone == zone)
    return list(db.scalars(query.order_by(Activity.id)).unique().all())


@router.get("/api/projects/{project_id}/activity-summary", response_model=ActivitySummary)
def activity_summary(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_or_404(db, Project, project_id, "Project")
    activities = list(db.scalars(select(Activity).where(Activity.project_id == project_id)).all())
    count = lambda state: sum(activity.status == state for activity in activities)
    average = (
        sum((activity.progress_percentage for activity in activities), Decimal("0")) / len(activities)
        if activities
        else Decimal("0")
    )
    return ActivitySummary(
        project_id=project_id,
        total_activities=len(activities),
        not_started=count(FieldActivityStatus.NOT_STARTED),
        started=count(FieldActivityStatus.STARTED),
        in_progress=count(FieldActivityStatus.IN_PROGRESS),
        submitted=count(FieldActivityStatus.SUBMITTED),
        verified=count(FieldActivityStatus.VERIFIED),
        completed=count(FieldActivityStatus.COMPLETED),
        delayed=0,
        average_progress=average,
    )
