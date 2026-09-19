from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity
from app.models.safety import (
    SafetyIncident, SafetyIncidentSeverity, SafetyIncidentStatus,
    SafetyIncidentType,
)
from app.models.construction_event import ConstructionEventType
from app.routes.events import _assigned_activity_ids
from app.schemas.safety import SafetyIncidentCreate, SafetyIncidentResponse, SafetySummary
from app.services.events.event_service import create_event
from app.services.notifications.notification_service import notify_safety_incident

router = APIRouter(tags=["safety"])
MANAGEMENT = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
PROJECT_SAFETY_ROLES = MANAGEMENT | {
    UserRole.SAFETY_OFFICER, UserRole.QA_QC_ENGINEER,
    UserRole.FIELD_ENGINEER, UserRole.SITE_ENGINEER,
}
REPORTING_ROLES = PROJECT_SAFETY_ROLES | {UserRole.WORKER, UserRole.FOREMAN}


def _project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")


def _access(db: Session, project_id: int, user: User, activity_id: int | None = None) -> set[int] | None:
    _project(db, project_id)
    if user.role in PROJECT_SAFETY_ROLES:
        return None
    assigned = _assigned_activity_ids(db, user.id, project_id)
    if user.role not in REPORTING_ROLES or not assigned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for safety records")
    if activity_id is not None and activity_id not in assigned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    return assigned


def _activity(db: Session, project_id: int, activity_id: int | None) -> Activity | None:
    if activity_id is None:
        return None
    activity = db.get(Activity, activity_id)
    if activity is None or activity.project_id != project_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity does not belong to project")
    return activity


@router.post("/api/projects/{project_id}/safety/incidents", response_model=SafetyIncidentResponse, status_code=201)
def create_incident(project_id: int, data: SafetyIncidentCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user, data.activity_id)
    activity = _activity(db, project_id, data.activity_id)
    if data.occurred_at > datetime.now(timezone.utc):
        raise HTTPException(422, "occurred_at cannot be in the future")
    incident = SafetyIncident(project_id=project_id, reported_by=current_user.id, **data.model_dump())
    db.add(incident)
    db.flush()
    create_event(
        db, project_id=project_id, activity_id=incident.activity_id,
        wbs_id=activity.wbs_id if activity else None,
        event_type=ConstructionEventType.SAFETY_INCIDENT,
        actor_user_id=current_user.id, event_timestamp=incident.occurred_at,
        latitude=incident.latitude, longitude=incident.longitude, zone=incident.zone,
        title=f"{incident.severity.value} safety incident reported",
        description=incident.description,
        metadata={"incident_type": incident.incident_type.value, "severity": incident.severity.value,
                  "create_memory": incident.severity in {SafetyIncidentSeverity.HIGH, SafetyIncidentSeverity.CRITICAL}},
        reference_type="safety_incident", reference_id=incident.id,
    )
    notify_safety_incident(db, incident, activity)
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/api/projects/{project_id}/safety/incidents", response_model=list[SafetyIncidentResponse])
def list_incidents(project_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    activity_ids = _access(db, project_id, current_user)
    query = select(SafetyIncident).where(SafetyIncident.project_id == project_id)
    if activity_ids is not None:
        query = query.where(SafetyIncident.activity_id.in_(activity_ids))
    return list(db.scalars(query.order_by(SafetyIncident.occurred_at.desc(), SafetyIncident.id.desc())).all())


@router.get("/api/safety/incidents/{incident_id}", response_model=SafetyIncidentResponse)
def incident_detail(incident_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    incident = db.get(SafetyIncident, incident_id)
    if incident is None:
        raise HTTPException(404, "Safety incident not found")
    activity_ids = _access(db, incident.project_id, current_user, incident.activity_id)
    if activity_ids is not None and incident.activity_id not in activity_ids:
        raise HTTPException(403, "You are not authorized for this incident")
    return incident


@router.get("/api/projects/{project_id}/safety/summary", response_model=SafetySummary)
def safety_summary(project_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    activity_ids = _access(db, project_id, current_user)
    query = select(SafetyIncident).where(SafetyIncident.project_id == project_id)
    if activity_ids is not None:
        query = query.where(SafetyIncident.activity_id.in_(activity_ids))
    incidents = list(db.scalars(query).all())
    return SafetySummary(
        project_id=project_id,
        total_incidents=len(incidents),
        open_incidents=sum(i.status == SafetyIncidentStatus.OPEN for i in incidents),
        critical_incidents=sum(i.severity == SafetyIncidentSeverity.CRITICAL for i in incidents),
        incidents_by_severity={severity.value: sum(i.severity == severity for i in incidents) for severity in SafetyIncidentSeverity},
        incidents_by_type={incident_type.value: sum(i.incident_type == incident_type for i in incidents) for incident_type in SafetyIncidentType},
    )
