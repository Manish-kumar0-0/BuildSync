from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import (
    Activity, AuditLog, Evidence, EvidenceStatus, Project, ProjectAssignmentStatus,
    ProjectConfiguration, ProjectStatus, ProjectUserAssignment, ProjectZone,
    QualityDefect, QualityDefectStatus, SafetyIncident, SafetyIncidentStatus,
    SiteDisruption, User, UserRole, MaterialItem, FieldActivityStatus,
)
from app.schemas.admin import (
    AdminOverview, AdminProjectCreate, AdminProjectResponse, AdminProjectUpdate,
    AuditLogResponse, ProjectConfigurationResponse, ProjectConfigurationUpdate,
    ProjectStatusUpdate, ProjectUserAssignmentCreate, ProjectUserAssignmentResponse,
    ProjectUserAssignmentUpdate, ProjectZoneCreate, ProjectZoneResponse,
    ProjectZoneUpdate,
)

router = APIRouter(prefix="/api", tags=["admin"])
ADMIN = {UserRole.ADMIN}
PROJECT_MANAGERS = ADMIN | {UserRole.PROJECT_MANAGER}
PROJECT_ACCESS_ROLES = PROJECT_MANAGERS | {
    UserRole.SITE_ENGINEER, UserRole.FIELD_ENGINEER, UserRole.SAFETY_OFFICER,
    UserRole.QA_QC_ENGINEER, UserRole.WORKER, UserRole.FOREMAN,
}
TRANSITIONS = {
    ProjectStatus.PLANNED: {ProjectStatus.PLANNED, ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.PLANNING: {ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD, ProjectStatus.ARCHIVED},
    ProjectStatus.ACTIVE: {ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED},
    ProjectStatus.ON_HOLD: {ProjectStatus.ON_HOLD, ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.COMPLETED: {ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: {ProjectStatus.ARCHIVED},
}


def _project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


def _admin(user: User) -> None:
    if user.role not in ADMIN:
        raise HTTPException(403, "Admin access is required")


def _can_view(db: Session, project_id: int, user: User) -> None:
    _project(db, project_id)
    if user.role in PROJECT_MANAGERS:
        return
    assigned = db.scalar(select(ProjectUserAssignment.id).where(
        ProjectUserAssignment.project_id == project_id,
        ProjectUserAssignment.user_id == user.id,
        ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE,
    ))
    if user.role not in PROJECT_ACCESS_ROLES or assigned is None:
        raise HTTPException(403, "You are not authorized for this project")


def _audit(db: Session, user_id: int, action: str, entity_type: str,
           entity_id: int | None, project_id: int | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type,
                    entity_id=entity_id, project_id=project_id))


@router.post("/admin/projects", response_model=AdminProjectResponse, status_code=201)
def create_project(data: AdminProjectCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    _admin(current_user)
    if db.scalar(select(Project.id).where(Project.project_code == data.project_code)):
        raise HTTPException(409, "Project code already exists")
    project = Project(**data.model_dump(), status=ProjectStatus.PLANNED, created_by=current_user.id)
    db.add(project)
    db.flush()
    _audit(db, current_user.id, "PROJECT_CREATED", "project", project.id, project.id)
    db.commit()
    db.refresh(project)
    return project


@router.get("/admin/projects", response_model=list[AdminProjectResponse])
def list_admin_projects(db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    _admin(current_user)
    return list(db.scalars(select(Project).order_by(Project.id.desc())).all())


@router.get("/admin/projects/{project_id}", response_model=AdminProjectResponse)
def get_admin_project(project_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    _can_view(db, project_id, current_user)
    return _project(db, project_id)


@router.patch("/admin/projects/{project_id}", response_model=AdminProjectResponse)
def update_admin_project(project_id: int, data: AdminProjectUpdate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    _admin(current_user)
    project = _project(db, project_id)
    values = data.model_dump(exclude_unset=True)
    if "project_code" in values and db.scalar(select(Project.id).where(
        Project.project_code == values["project_code"], Project.id != project_id)):
        raise HTTPException(409, "Project code already exists")
    start = values.get("start_date", project.start_date)
    end = values.get("planned_end_date", project.planned_end_date)
    if end < start:
        raise HTTPException(422, "planned_end_date cannot be before start_date")
    for key, value in values.items():
        setattr(project, key, value)
    _audit(db, current_user.id, "PROJECT_UPDATED", "project", project.id, project.id)
    db.commit()
    db.refresh(project)
    return project


@router.post("/admin/projects/{project_id}/users", response_model=ProjectUserAssignmentResponse, status_code=201)
def assign_project_user(project_id: int, data: ProjectUserAssignmentCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    _admin(current_user)
    _project(db, project_id)
    user = db.get(User, data.user_id)
    if user is None or not user.is_active:
        raise HTTPException(404, "Active user not found")
    existing = db.scalar(select(ProjectUserAssignment).where(
        ProjectUserAssignment.project_id == project_id, ProjectUserAssignment.user_id == data.user_id,
        ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE))
    if existing:
        raise HTTPException(409, "User is already actively assigned to this project")
    assignment = ProjectUserAssignment(project_id=project_id, **data.model_dump())
    db.add(assignment)
    db.flush()
    _audit(db, current_user.id, "USER_ASSIGNED", "project_user_assignment", assignment.id, project_id)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/admin/projects/{project_id}/users", response_model=list[ProjectUserAssignmentResponse])
def list_project_users(project_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    _can_view(db, project_id, current_user)
    return list(db.scalars(select(ProjectUserAssignment).where(
        ProjectUserAssignment.project_id == project_id).order_by(ProjectUserAssignment.id)).all())


@router.patch("/admin/projects/{project_id}/users/{user_id}", response_model=ProjectUserAssignmentResponse)
def update_project_user(project_id: int, user_id: int, data: ProjectUserAssignmentUpdate,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    _project(db, project_id)
    assignment = db.scalar(select(ProjectUserAssignment).where(
        ProjectUserAssignment.project_id == project_id, ProjectUserAssignment.user_id == user_id,
        ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE))
    if assignment is None:
        raise HTTPException(404, "Active project user assignment not found")
    values = data.model_dump(exclude_unset=True)
    if values.get("status") == ProjectAssignmentStatus.INACTIVE:
        assignment.removed_at = datetime.now(timezone.utc)
        _audit(db, current_user.id, "USER_REMOVED", "project_user_assignment", assignment.id, project_id)
    elif "role" in values:
        _audit(db, current_user.id, "USER_ROLE_UPDATED", "project_user_assignment", assignment.id, project_id)
    for key, value in values.items():
        setattr(assignment, key, value)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/projects/{project_id}/configuration", response_model=ProjectConfigurationResponse)
def get_configuration(project_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    _can_view(db, project_id, current_user)
    config = db.scalar(select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id))
    if config is None:
        return ProjectConfigurationResponse(project_id=project_id, timezone="UTC",
            default_zone=None, progress_update_frequency="DAILY", evidence_required=True)
    return config


@router.patch("/projects/{project_id}/configuration", response_model=ProjectConfigurationResponse)
def update_configuration(project_id: int, data: ProjectConfigurationUpdate,
                         db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    _project(db, project_id)
    config = db.scalar(select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id))
    if config is None:
        config = ProjectConfiguration(project_id=project_id)
        db.add(config)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


@router.post("/projects/{project_id}/zones", response_model=ProjectZoneResponse, status_code=201)
def create_zone(project_id: int, data: ProjectZoneCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    _admin(current_user)
    _project(db, project_id)
    zone = ProjectZone(project_id=project_id, **data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/projects/{project_id}/zones", response_model=list[ProjectZoneResponse])
def list_zones(project_id: int, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    _can_view(db, project_id, current_user)
    return list(db.scalars(select(ProjectZone).where(ProjectZone.project_id == project_id).order_by(ProjectZone.name)).all())


@router.patch("/projects/{project_id}/zones/{zone_id}", response_model=ProjectZoneResponse)
def update_zone(project_id: int, zone_id: int, data: ProjectZoneUpdate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    _admin(current_user)
    _project(db, project_id)
    zone = db.scalar(select(ProjectZone).where(ProjectZone.id == zone_id, ProjectZone.project_id == project_id))
    if zone is None:
        raise HTTPException(404, "Project zone not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.patch("/admin/projects/{project_id}/status", response_model=AdminProjectResponse)
def update_status(project_id: int, data: ProjectStatusUpdate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    _admin(current_user)
    project = _project(db, project_id)
    if data.status not in TRANSITIONS[project.status]:
        raise HTTPException(422, f"Invalid project status transition from {project.status.value}")
    project.status = data.status
    if data.status == ProjectStatus.COMPLETED and project.actual_end_date is None:
        project.actual_end_date = datetime.now(timezone.utc).date()
    _audit(db, current_user.id, "PROJECT_STATUS_CHANGED", "project", project.id, project.id)
    db.commit()
    db.refresh(project)
    return project


@router.get("/admin/projects/{project_id}/overview", response_model=AdminOverview)
def project_overview(project_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    _admin(current_user)
    project = _project(db, project_id)
    users_count = db.scalar(select(func.count()).select_from(ProjectUserAssignment).where(
        ProjectUserAssignment.project_id == project_id,
        ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE)) or 0
    active_activities = db.scalar(select(func.count()).select_from(Activity).where(
        Activity.project_id == project_id, Activity.status == FieldActivityStatus.IN_PROGRESS)) or 0
    pending_evidence = db.scalar(select(func.count()).select_from(Evidence).where(
        Evidence.project_id == project_id, Evidence.status == EvidenceStatus.VERIFICATION_PENDING)) or 0
    open_safety = db.scalar(select(func.count()).select_from(SafetyIncident).where(
        SafetyIncident.project_id == project_id, SafetyIncident.status != SafetyIncidentStatus.RESOLVED)) or 0
    open_defects = db.scalar(select(func.count()).select_from(QualityDefect).where(
        QualityDefect.project_id == project_id,
        QualityDefect.status.in_([QualityDefectStatus.OPEN, QualityDefectStatus.IN_PROGRESS]))) or 0
    active_disruptions = db.scalar(select(func.count()).select_from(SiteDisruption).where(
        SiteDisruption.project_id == project_id, SiteDisruption.end_time.is_(None))) or 0
    low_stock = db.scalar(select(func.count()).select_from(MaterialItem).where(
        MaterialItem.project_id == project_id,
        MaterialItem.current_quantity <= MaterialItem.minimum_stock_level)) or 0
    return AdminOverview(project=project, users_count=users_count, active_activities=active_activities,
        pending_evidence=pending_evidence, open_safety_incidents=open_safety,
        open_quality_defects=open_defects, active_disruptions=active_disruptions,
        low_stock_materials=low_stock)


@router.get("/admin/projects/{project_id}/audit", response_model=list[AuditLogResponse])
def project_audit(project_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    _admin(current_user)
    _project(db, project_id)
    return list(db.scalars(select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.created_at.desc())).all())
