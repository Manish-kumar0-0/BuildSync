from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.models import (
    ActivityStatus,
    BOQItem,
    PlannedProgress,
    Project,
    ProjectAssignmentStatus,
    ProjectUserAssignment,
    ScheduleActivity,
    User,
    UserRole,
    WBS,
)
from app.schemas.planning import (
    BOQCreate, BOQResponse, BOQUpdate, PlanSummary, PlannedProgressCreate,
    PlannedProgressResponse, ProjectCreate, ProjectResponse, ProjectUpdate,
    ScheduleCreate, ScheduleResponse, ScheduleUpdate, WBSCreate, WBSResponse, WBSUpdate,
)

router = APIRouter(tags=["project planning"])
manager = Depends(require_role(UserRole.PROJECT_MANAGER, UserRole.ADMIN))


def get_or_404(db: Session, model: type, item_id: int, label: str):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, f"{label} not found")
    return item


def project_or_404(db: Session, project_id: int) -> Project:
    return get_or_404(db, Project, project_id, "Project")


def same_project(db: Session, model: type, item_id: int | None, project_id: int, label: str) -> None:
    if item_id is not None:
        item = get_or_404(db, model, item_id, label)
        if item.project_id != project_id:
            raise HTTPException(422, f"{label} must belong to the same project")


def commit_refresh(db: Session, item):
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/api/projects", response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db), user: User = manager):
    if db.scalar(select(Project.id).where(Project.project_code == data.project_code)):
        raise HTTPException(409, "Project code already exists")
    return commit_refresh(db, Project(**data.model_dump(), created_by=user.id))


@router.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in {UserRole.ADMIN, UserRole.PROJECT_MANAGER}:
        query = select(Project)
    else:
        query = (
            select(Project)
            .join(
                ProjectUserAssignment,
                ProjectUserAssignment.project_id == Project.id,
            )
            .where(
                ProjectUserAssignment.user_id == current_user.id,
                ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE,
            )
        )
    return list(db.scalars(query.order_by(Project.id.desc())).unique().all())


@router.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return project_or_404(db, project_id)


@router.put("/api/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db), _: User = manager):
    project = project_or_404(db, project_id)
    values = data.model_dump(exclude_unset=True)
    start = values.get("start_date", project.start_date)
    end = values.get("planned_end_date", project.planned_end_date)
    if end < start:
        raise HTTPException(422, "planned_end_date cannot be before start_date")
    for key, value in values.items():
        setattr(project, key, value)
    return commit_refresh(db, project)


@router.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), _: User = manager):
    db.delete(project_or_404(db, project_id))
    db.commit()


@router.post("/api/projects/{project_id}/wbs", response_model=WBSResponse, status_code=201)
def create_wbs(project_id: int, data: WBSCreate, db: Session = Depends(get_db), _: User = manager):
    project_or_404(db, project_id)
    same_project(db, WBS, data.parent_id, project_id, "Parent WBS")
    return commit_refresh(db, WBS(project_id=project_id, **data.model_dump()))


@router.get("/api/projects/{project_id}/wbs", response_model=list[WBSResponse])
def list_wbs(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    return list(db.scalars(select(WBS).where(WBS.project_id == project_id).order_by(WBS.wbs_code)).all())


@router.get("/api/wbs/{wbs_id}", response_model=WBSResponse)
def get_wbs(wbs_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_or_404(db, WBS, wbs_id, "WBS")


@router.put("/api/wbs/{wbs_id}", response_model=WBSResponse)
def update_wbs(wbs_id: int, data: WBSUpdate, db: Session = Depends(get_db), _: User = manager):
    item = get_or_404(db, WBS, wbs_id, "WBS")
    values = data.model_dump(exclude_unset=True)
    if "parent_id" in values:
        same_project(db, WBS, values["parent_id"], item.project_id, "Parent WBS")
        if values["parent_id"] == item.id:
            raise HTTPException(422, "WBS cannot be its own parent")
    for key, value in values.items():
        setattr(item, key, value)
    return commit_refresh(db, item)


@router.delete("/api/wbs/{wbs_id}", status_code=204)
def delete_wbs(wbs_id: int, db: Session = Depends(get_db), _: User = manager):
    db.delete(get_or_404(db, WBS, wbs_id, "WBS"))
    db.commit()


@router.post("/api/projects/{project_id}/boq", response_model=BOQResponse, status_code=201)
def create_boq(project_id: int, data: BOQCreate, db: Session = Depends(get_db), _: User = manager):
    project_or_404(db, project_id)
    same_project(db, WBS, data.wbs_id, project_id, "WBS")
    return commit_refresh(db, BOQItem(project_id=project_id, **data.model_dump()))


@router.get("/api/projects/{project_id}/boq", response_model=list[BOQResponse])
def list_boq(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    return list(db.scalars(select(BOQItem).where(BOQItem.project_id == project_id)).all())


@router.get("/api/boq/{boq_id}", response_model=BOQResponse)
def get_boq(boq_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_or_404(db, BOQItem, boq_id, "BOQ item")


@router.put("/api/boq/{boq_id}", response_model=BOQResponse)
def update_boq(boq_id: int, data: BOQUpdate, db: Session = Depends(get_db), _: User = manager):
    item = get_or_404(db, BOQItem, boq_id, "BOQ item")
    values = data.model_dump(exclude_unset=True)
    same_project(db, WBS, values.get("wbs_id"), item.project_id, "WBS")
    for key, value in values.items():
        setattr(item, key, value)
    return commit_refresh(db, item)


@router.delete("/api/boq/{boq_id}", status_code=204)
def delete_boq(boq_id: int, db: Session = Depends(get_db), _: User = manager):
    db.delete(get_or_404(db, BOQItem, boq_id, "BOQ item"))
    db.commit()


@router.post("/api/projects/{project_id}/schedule", response_model=ScheduleResponse, status_code=201)
def create_schedule(project_id: int, data: ScheduleCreate, db: Session = Depends(get_db), _: User = manager):
    project_or_404(db, project_id)
    same_project(db, WBS, data.wbs_id, project_id, "WBS")
    same_project(db, BOQItem, data.boq_item_id, project_id, "BOQ item")
    return commit_refresh(db, ScheduleActivity(project_id=project_id, **data.model_dump()))


@router.get("/api/projects/{project_id}/schedule", response_model=list[ScheduleResponse])
def list_schedule(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    return list(db.scalars(select(ScheduleActivity).where(ScheduleActivity.project_id == project_id)).all())


@router.get("/api/schedule/{activity_id}", response_model=ScheduleResponse)
def get_schedule(activity_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_or_404(db, ScheduleActivity, activity_id, "Schedule activity")


@router.put("/api/schedule/{activity_id}", response_model=ScheduleResponse)
def update_schedule(activity_id: int, data: ScheduleUpdate, db: Session = Depends(get_db), _: User = manager):
    activity = get_or_404(db, ScheduleActivity, activity_id, "Schedule activity")
    values = data.model_dump(exclude_unset=True)
    same_project(db, WBS, values.get("wbs_id"), activity.project_id, "WBS")
    same_project(db, BOQItem, values.get("boq_item_id"), activity.project_id, "BOQ item")
    start = values.get("planned_start", activity.planned_start)
    finish = values.get("planned_finish", activity.planned_finish)
    if finish < start:
        raise HTTPException(422, "planned_finish cannot be before planned_start")
    for key, value in values.items():
        setattr(activity, key, value)
    return commit_refresh(db, activity)


@router.delete("/api/schedule/{activity_id}", status_code=204)
def delete_schedule(activity_id: int, db: Session = Depends(get_db), _: User = manager):
    db.delete(get_or_404(db, ScheduleActivity, activity_id, "Schedule activity"))
    db.commit()


@router.post("/api/schedule/{activity_id}/planned-progress", response_model=PlannedProgressResponse, status_code=201)
def create_progress(activity_id: int, data: PlannedProgressCreate, db: Session = Depends(get_db), _: User = manager):
    get_or_404(db, ScheduleActivity, activity_id, "Schedule activity")
    return commit_refresh(db, PlannedProgress(schedule_activity_id=activity_id, **data.model_dump()))


@router.get("/api/schedule/{activity_id}/planned-progress", response_model=list[PlannedProgressResponse])
def list_progress(activity_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_or_404(db, ScheduleActivity, activity_id, "Schedule activity")
    return list(db.scalars(select(PlannedProgress).where(PlannedProgress.schedule_activity_id == activity_id).order_by(PlannedProgress.date)).all())


@router.get("/api/projects/{project_id}/plan-summary", response_model=PlanSummary)
def plan_summary(project_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project = project_or_404(db, project_id)
    wbs = list(db.scalars(select(WBS).where(WBS.project_id == project_id)).all())
    boq = list(db.scalars(select(BOQItem).where(BOQItem.project_id == project_id)).all())
    activities = list(db.scalars(select(ScheduleActivity).where(ScheduleActivity.project_id == project_id)).all())
    counts = {status.value: sum(activity.status == status for activity in activities) for status in ActivityStatus}
    upcoming = [a for a in activities if a.planned_start >= date.today() and a.status == ActivityStatus.NOT_STARTED]
    delayed = [a for a in activities if a.status == ActivityStatus.DELAYED]
    overall = (
        sum((a.planned_progress * a.weightage for a in activities), Decimal("0"))
        / sum((a.weightage for a in activities), Decimal("1"))
    )
    return PlanSummary(
        project=project, total_wbs_items=len(wbs), total_boq_items=len(boq),
        total_schedule_activities=len(activities), overall_planned_progress=overall,
        activities_by_status=counts, upcoming_activities=upcoming, delayed_activities=delayed,
    )
