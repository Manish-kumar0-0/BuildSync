from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.construction_event import ConstructionEventType
from app.models.field_activity import Activity
from app.models.quality import (
    InspectionStatus, QualityDefect, QualityDefectStatus, QualityInspection,
    QualitySeverity,
)
from app.routes.events import _assigned_activity_ids
from app.schemas.quality import (
    ActivityQualityResponse, QualityDefectCreate, QualityDefectResponse,
    QualityInspectionCreate, QualityInspectionResponse, QualitySummary,
)
from app.services.events.event_service import create_event
from app.services.notifications.notification_service import notify_quality_issue

router = APIRouter(tags=["quality"])
MANAGEMENT = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
QUALITY_MANAGERS = MANAGEMENT | {UserRole.QA_QC_ENGINEER, UserRole.SITE_ENGINEER}
QUALITY_VIEWERS = QUALITY_MANAGERS | {UserRole.FIELD_ENGINEER}


def _project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")


def _access(db: Session, project_id: int, user: User, activity_id: int | None = None,
            manage: bool = False) -> set[int] | None:
    _project(db, project_id)
    if user.role in QUALITY_MANAGERS:
        return None
    if manage:
        raise HTTPException(403, "QA/QC management access is required")
    assigned = _assigned_activity_ids(db, user.id, project_id)
    if user.role not in QUALITY_VIEWERS | {UserRole.WORKER, UserRole.FOREMAN} or not assigned:
        raise HTTPException(403, "You are not authorized for quality records")
    if activity_id is not None and activity_id not in assigned:
        raise HTTPException(403, "You are not authorized for this activity")
    return assigned


def _activity(db: Session, project_id: int, activity_id: int | None) -> Activity | None:
    if activity_id is None:
        return None
    activity = db.get(Activity, activity_id)
    if activity is None or activity.project_id != project_id:
        raise HTTPException(422, "Activity does not belong to project")
    return activity


@router.post("/api/projects/{project_id}/quality/inspections", response_model=QualityInspectionResponse, status_code=201)
def create_inspection(project_id: int, data: QualityInspectionCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user, data.activity_id, manage=True)
    activity = _activity(db, project_id, data.activity_id)
    if data.inspected_at > datetime.now(timezone.utc):
        raise HTTPException(422, "inspected_at cannot be in the future")
    inspection = QualityInspection(project_id=project_id, inspector_id=current_user.id, **data.model_dump())
    db.add(inspection)
    db.flush()
    if inspection.status == InspectionStatus.FAILED:
        create_event(
            db, project_id=project_id, activity_id=inspection.activity_id,
            wbs_id=activity.wbs_id if activity else None,
            event_type=ConstructionEventType.QUALITY_INSPECTION_FAILED,
            actor_user_id=current_user.id, event_timestamp=inspection.inspected_at,
            title="Quality inspection failed", description=inspection.notes,
            metadata={"inspection_id": inspection.id, "score": inspection.score},
            reference_type="quality_inspection", reference_id=inspection.id,
        )
        notify_quality_issue(
            db,
            project_id=project_id,
            entity_id=inspection.id,
            title="Quality inspection failed",
            message=inspection.notes or "A quality inspection failed.",
            activity=activity,
        )
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("/api/projects/{project_id}/quality/inspections", response_model=list[QualityInspectionResponse])
def list_inspections(project_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    activity_ids = _access(db, project_id, current_user)
    query = select(QualityInspection).where(QualityInspection.project_id == project_id)
    if activity_ids is not None:
        query = query.where(QualityInspection.activity_id.in_(activity_ids))
    return list(db.scalars(query.order_by(QualityInspection.inspected_at.desc(), QualityInspection.id.desc())).all())


@router.get("/api/quality/inspections/{inspection_id}", response_model=QualityInspectionResponse)
def inspection_detail(inspection_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    inspection = db.get(QualityInspection, inspection_id)
    if inspection is None:
        raise HTTPException(404, "Quality inspection not found")
    activity_ids = _access(db, inspection.project_id, current_user, inspection.activity_id)
    if activity_ids is not None and inspection.activity_id not in activity_ids:
        raise HTTPException(403, "You are not authorized for this inspection")
    return inspection


@router.post("/api/quality/inspections/{inspection_id}/defects", response_model=QualityDefectResponse, status_code=201)
def create_defect(inspection_id: int, data: QualityDefectCreate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    inspection = db.get(QualityInspection, inspection_id)
    if inspection is None:
        raise HTTPException(404, "Quality inspection not found")
    _access(db, inspection.project_id, current_user, data.activity_id or inspection.activity_id, manage=True)
    activity_id = data.activity_id or inspection.activity_id
    activity = _activity(db, inspection.project_id, activity_id)
    if data.inspection_id is not None and data.inspection_id != inspection_id:
        raise HTTPException(422, "inspection_id must match the path")
    if inspection.activity_id is not None and activity_id != inspection.activity_id:
        raise HTTPException(422, "Defect activity must match the inspection activity")
    defect = QualityDefect(
        project_id=inspection.project_id, inspection_id=inspection.id,
        activity_id=activity_id, reported_by=current_user.id,
        severity=data.severity, description=data.description, location=data.location,
    )
    db.add(defect)
    db.flush()
    if defect.severity in {QualitySeverity.HIGH, QualitySeverity.CRITICAL}:
        create_event(
            db, project_id=defect.project_id, activity_id=defect.activity_id,
            wbs_id=activity.wbs_id if activity else None,
            event_type=ConstructionEventType.QUALITY_DEFECT,
            actor_user_id=current_user.id, title=f"{defect.severity.value} quality defect",
            description=defect.description,
            metadata={"defect_id": defect.id, "severity": defect.severity.value},
            reference_type="quality_defect", reference_id=defect.id,
        )
        notify_quality_issue(
            db,
            project_id=defect.project_id,
            entity_id=defect.id,
            title=f"{defect.severity.value.title()} quality defect reported",
            message=defect.description,
            activity=activity,
        )
    db.commit()
    db.refresh(defect)
    return defect


@router.get("/api/activities/{activity_id}/quality", response_model=ActivityQualityResponse)
def activity_quality(activity_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(404, "Field activity not found")
    _access(db, activity.project_id, current_user, activity_id)
    latest = db.scalar(select(QualityInspection).where(
        QualityInspection.activity_id == activity_id
    ).order_by(QualityInspection.inspected_at.desc(), QualityInspection.id.desc()).limit(1))
    defects = list(db.scalars(select(QualityDefect).where(QualityDefect.activity_id == activity_id)).all())
    return ActivityQualityResponse(
        latest_inspection=latest, latest_score=latest.score if latest else None,
        inspection_status=latest.status if latest else None,
        open_defects=sum(d.status in {QualityDefectStatus.OPEN, QualityDefectStatus.IN_PROGRESS} for d in defects),
        critical_defects=sum(d.severity == QualitySeverity.CRITICAL and d.status != QualityDefectStatus.RESOLVED for d in defects),
    )


@router.get("/api/projects/{project_id}/quality/summary", response_model=QualitySummary)
def quality_summary(project_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    activity_ids = _access(db, project_id, current_user)
    inspection_query = select(QualityInspection).where(QualityInspection.project_id == project_id)
    defect_query = select(QualityDefect).where(QualityDefect.project_id == project_id)
    if activity_ids is not None:
        inspection_query = inspection_query.where(QualityInspection.activity_id.in_(activity_ids))
        defect_query = defect_query.where(QualityDefect.activity_id.in_(activity_ids))
    inspections = list(db.scalars(inspection_query).all())
    defects = list(db.scalars(defect_query).all())
    return QualitySummary(
        project_id=project_id, total_inspections=len(inspections),
        passed=sum(i.status == InspectionStatus.PASSED for i in inspections),
        failed=sum(i.status == InspectionStatus.FAILED for i in inspections),
        conditional=sum(i.status == InspectionStatus.CONDITIONAL for i in inspections),
        open_defects=sum(d.status in {QualityDefectStatus.OPEN, QualityDefectStatus.IN_PROGRESS} for d in defects),
        critical_defects=sum(d.severity == QualitySeverity.CRITICAL and d.status != QualityDefectStatus.RESOLVED for d in defects),
    )
