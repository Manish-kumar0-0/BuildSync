from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity
from app.models.progress_assessment import ProgressAssessment
from app.models.risk_prediction import ActivityRiskPrediction
from app.models.site_disruption import (
    SiteDisruption,
    SiteDisruptionSeverity,
    SiteDisruptionType,
)
from app.models.construction_event import ConstructionEventType
from app.routes.events import _activity, _assigned_activity_ids
from app.schemas.site_disruption import (
    ActiveDisruptionsResponse,
    ActivityDisruptionsResponse,
    DisruptionImpactResponse,
    DisruptionSummaryResponse,
    SiteDisruptionCreate,
    SiteDisruptionListResponse,
    SiteDisruptionResponse,
)
from app.services.events.event_service import create_event

router = APIRouter(tags=["site disruptions"])
MANAGEMENT_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
WEATHER_TYPES = {
    SiteDisruptionType.WEATHER,
    SiteDisruptionType.RAIN,
    SiteDisruptionType.HEAT,
    SiteDisruptionType.STORM,
    SiteDisruptionType.HIGH_WIND,
    SiteDisruptionType.FLOODING,
    SiteDisruptionType.LIGHTNING,
    SiteDisruptionType.VISIBILITY,
}


def _project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


def _can_access_project(db: Session, project_id: int, user: User) -> bool:
    if user.role in MANAGEMENT_ROLES:
        return True
    return bool(_assigned_activity_ids(db, user.id, project_id))


def _can_access_activity(db: Session, activity: Activity, user: User) -> bool:
    return user.role in MANAGEMENT_ROLES or activity.id in _assigned_activity_ids(
        db, user.id, activity.project_id
    )


def _scope_condition(db: Session, project_id: int, user: User):
    if user.role in MANAGEMENT_ROLES:
        return None
    assigned_ids = _assigned_activity_ids(db, user.id, project_id)
    if user.role == UserRole.SITE_ENGINEER:
        return or_(
            SiteDisruption.activity_id.is_(None),
            SiteDisruption.activity_id.in_(assigned_ids),
        )
    return SiteDisruption.activity_id.in_(assigned_ids)


def _authorize_project(db: Session, project_id: int, user: User) -> None:
    _project(db, project_id)
    if not _can_access_project(db, project_id, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project")


def _authorize_disruption_activity(
    db: Session, project_id: int, activity_id: int | None, user: User
) -> Activity | None:
    if activity_id is None:
        if user.role not in MANAGEMENT_ROLES and user.role != UserRole.SITE_ENGINEER:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "An activity is required for your role",
            )
        if user.role == UserRole.SITE_ENGINEER and not _can_access_project(
            db, project_id, user
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You are not authorized for this project",
            )
        return None
    activity = _activity(db, activity_id)
    if activity.project_id != project_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity does not belong to this project")
    if not _can_access_activity(db, activity, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    return activity


def _duration(disruption: SiteDisruption, now: datetime | None = None) -> int | None:
    if disruption.end_time is not None:
        return disruption.duration_minutes
    current = now or datetime.now(timezone.utc)
    start = disruption.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return max(0, int((current - start).total_seconds() // 60))


def _payload(disruption: SiteDisruption, dynamic_duration: bool = False) -> dict:
    return {
        "id": disruption.id,
        "project_id": disruption.project_id,
        "activity_id": disruption.activity_id,
        "type": disruption.type,
        "severity": disruption.severity,
        "start_time": disruption.start_time,
        "end_time": disruption.end_time,
        "duration_minutes": _duration(disruption) if dynamic_duration else disruption.duration_minutes,
        "zone": disruption.zone,
        "latitude": disruption.latitude,
        "longitude": disruption.longitude,
        "description": disruption.description,
        "source": disruption.source,
        "created_by": disruption.created_by,
        "created_at": disruption.created_at,
    }


@router.post(
    "/api/projects/{project_id}/disruptions",
    response_model=SiteDisruptionResponse,
)
def create_disruption(
    project_id: int,
    data: SiteDisruptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SiteDisruptionResponse:
    _project(db, project_id)
    _authorize_disruption_activity(
        db, project_id, data.activity_id, current_user
    )
    disruption = SiteDisruption(
        project_id=project_id,
        activity_id=data.activity_id,
        type=data.type,
        severity=data.severity,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_minutes=(
            int((data.end_time - data.start_time).total_seconds() // 60)
            if data.end_time is not None
            else None
        ),
        zone=data.zone,
        latitude=data.latitude,
        longitude=data.longitude,
        description=data.description,
        source=data.source,
        created_by=current_user.id,
    )
    db.add(disruption)
    db.flush()
    event_type = (
        ConstructionEventType.WEATHER_INTERRUPTION
        if data.type in WEATHER_TYPES
        else ConstructionEventType.SYSTEM_EVENT
    )
    create_event(
        db,
        project_id=project_id,
        activity_id=data.activity_id,
        event_type=event_type,
        title=f"{data.type.value.replace('_', ' ').title()} site disruption",
        description=data.description,
        actor_user_id=current_user.id,
        event_timestamp=data.start_time,
        latitude=data.latitude,
        longitude=data.longitude,
        zone=data.zone,
        metadata={
            "disruption_id": disruption.id,
            "disruption_type": data.type.value,
            "severity": data.severity.value,
            "duration_minutes": disruption.duration_minutes,
            "source": data.source.value,
            "description": data.description,
        },
        reference_type="site_disruption",
        reference_id=disruption.id,
    )
    db.commit()
    db.refresh(disruption)
    return SiteDisruptionResponse.model_validate(_payload(disruption))


@router.get(
    "/api/projects/{project_id}/disruptions/active",
    response_model=ActiveDisruptionsResponse,
)
def active_disruptions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _authorize_project(db, project_id, current_user)
    now = datetime.now(timezone.utc)
    active_query = select(SiteDisruption).where(
            SiteDisruption.project_id == project_id,
            SiteDisruption.start_time <= now,
            (SiteDisruption.end_time.is_(None) | (SiteDisruption.end_time > now)),
        )
    scope = _scope_condition(db, project_id, current_user)
    if scope is not None:
        active_query = active_query.where(scope)
    items = db.scalars(
        active_query.order_by(SiteDisruption.start_time.asc())
    ).all()
    return {"active_disruptions": [_payload(item, dynamic_duration=True) for item in items]}


@router.get(
    "/api/projects/{project_id}/disruptions",
    response_model=SiteDisruptionListResponse,
)
def list_disruptions(
    project_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    type: SiteDisruptionType | None = None,
    severity: SiteDisruptionSeverity | None = None,
    zone: str | None = None,
    activity_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _authorize_project(db, project_id, current_user)
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "start_date must not exceed end_date")
    query = select(SiteDisruption).where(SiteDisruption.project_id == project_id)
    scope = _scope_condition(db, project_id, current_user)
    if scope is not None:
        query = query.where(scope)
    if activity_id is not None:
        activity = _authorize_disruption_activity(db, project_id, activity_id, current_user)
        query = query.where(SiteDisruption.activity_id == activity.id)
    if start_date is not None:
        query = query.where(
            SiteDisruption.start_time
            >= datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        )
    if end_date is not None:
        query = query.where(
            SiteDisruption.start_time
            < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    if type is not None:
        query = query.where(SiteDisruption.type == type)
    if severity is not None:
        query = query.where(SiteDisruption.severity == severity)
    if zone is not None:
        query = query.where(SiteDisruption.zone == zone)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(SiteDisruption.start_time.desc(), SiteDisruption.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_payload(item) for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get(
    "/api/activities/{activity_id}/disruptions",
    response_model=ActivityDisruptionsResponse,
)
def activity_disruptions(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity = _activity(db, activity_id)
    if not _can_access_activity(db, activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    items = db.scalars(
        select(SiteDisruption)
        .where(SiteDisruption.activity_id == activity_id)
        .order_by(SiteDisruption.start_time.asc(), SiteDisruption.id.asc())
    ).all()
    return {
        "activity_id": activity.id,
        "activity_name": activity.name,
        "disruptions": [_payload(item) for item in items],
    }


@router.get(
    "/api/disruptions/{disruption_id}/impact",
    response_model=DisruptionImpactResponse,
)
def disruption_impact(
    disruption_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    disruption = db.get(SiteDisruption, disruption_id)
    if disruption is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Disruption not found")
    _authorize_project(db, disruption.project_id, current_user)
    activity = (
        db.get(Activity, disruption.activity_id)
        if disruption.activity_id is not None
        else None
    )
    if activity is None and current_user.role not in MANAGEMENT_ROLES | {
        UserRole.SITE_ENGINEER
    }:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this disruption")
    if activity is not None and not _can_access_activity(db, activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    progress_rows = (
        db.scalars(
            select(ProgressAssessment)
            .where(
                ProgressAssessment.activity_id == activity.id,
                ProgressAssessment.reported_progress.is_not(None),
            )
            .order_by(
                ProgressAssessment.assessment_date.desc(),
                ProgressAssessment.id.desc(),
            )
            .limit(2)
        ).all()
        if activity is not None
        else []
    )
    delay = (
        db.scalar(
            select(ActivityRiskPrediction.predicted_delay_days)
            .where(ActivityRiskPrediction.activity_id == activity.id)
            .order_by(
                ActivityRiskPrediction.prediction_date.desc(),
                ActivityRiskPrediction.id.desc(),
            )
            .limit(1)
        )
        if activity is not None
        else None
    )
    return {
        "disruption": {
            "id": disruption.id,
            "type": disruption.type,
            "severity": disruption.severity,
            "duration_minutes": disruption.duration_minutes,
        },
        "affected_activity": (
            {"id": activity.id, "name": activity.name} if activity else None
        ),
        "progress_context": {
            "latest_reported_progress": progress_rows[0].reported_progress
            if progress_rows
            else None,
            "previous_reported_progress": progress_rows[1].reported_progress
            if len(progress_rows) > 1
            else None,
        },
        "delay_context": {"predicted_delay_days": delay},
    }


@router.get(
    "/api/projects/{project_id}/disruptions/summary",
    response_model=DisruptionSummaryResponse,
)
def disruption_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _authorize_project(db, project_id, current_user)
    query = select(SiteDisruption).where(SiteDisruption.project_id == project_id)
    scope = _scope_condition(db, project_id, current_user)
    if scope is not None:
        query = query.where(scope)
    disruptions = db.scalars(query).all()
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    zones: dict[str, int] = {}
    total_minutes = 0
    for item in disruptions:
        by_type[item.type.value] = by_type.get(item.type.value, 0) + 1
        by_severity[item.severity.value] = by_severity.get(item.severity.value, 0) + 1
        minutes = item.duration_minutes or 0
        total_minutes += minutes
        if item.zone:
            zones[item.zone] = zones.get(item.zone, 0) + minutes
    most_affected = [
        {"zone": zone, "interruption_minutes": minutes}
        for zone, minutes in sorted(zones.items(), key=lambda pair: pair[1], reverse=True)
    ]
    return {
        "total_disruptions": len(disruptions),
        "weather_disruptions": sum(item.type in WEATHER_TYPES for item in disruptions),
        "total_interruption_minutes": total_minutes,
        "by_type": by_type,
        "by_severity": by_severity,
        "most_affected_zones": most_affected,
    }
