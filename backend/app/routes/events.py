from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Evidence, Project, User, UserRole
from app.models.construction_event import ConstructionEvent, ConstructionEventType
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus
from app.models.planning import WBS
from app.schemas.construction_event import (
    ConstructionEventCreate,
    ConstructionEventListResponse,
    ConstructionEventResponse,
)
from app.services.events.event_service import (
    create_event,
    get_activity_events,
    get_event,
    get_project_events,
)
from app.services.events.timeline_service import (
    get_activity_timeline,
    get_daily_summary,
    get_project_timeline,
    resolve_project_range,
)
from app.services.events.replay_service import (
    build_replay,
    parse_replay_time,
)
from app.schemas.replay import ReplayResponse
from app.schemas.timeline import (
    ActivityTimelineResponse,
    DailySummaryResponse,
    ProjectTimelineResponse,
)

router = APIRouter(tags=["construction events"])
MANAGEMENT_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}


def _activity(db: Session, activity_id: int) -> Activity:
    item = db.get(Activity, activity_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field activity not found")
    return item


def _assigned_activity_ids(db: Session, user_id: int, project_id: int) -> set[int]:
    return set(
        db.scalars(
            select(ActivityAssignment.activity_id)
            .join(Activity, Activity.id == ActivityAssignment.activity_id)
            .where(
                Activity.project_id == project_id,
                ActivityAssignment.user_id == user_id,
                ActivityAssignment.status == AssignmentStatus.ACTIVE,
            )
        ).all()
    )


def _can_access_activity(db: Session, activity: Activity, user: User) -> bool:
    return user.role in MANAGEMENT_ROLES or activity.id in _assigned_activity_ids(
        db, user.id, activity.project_id
    )


def _can_access_event(db: Session, event: ConstructionEvent, user: User) -> bool:
    if user.role in MANAGEMENT_ROLES:
        return True
    assigned_ids = _assigned_activity_ids(db, user.id, event.project_id)
    if user.role == UserRole.SITE_ENGINEER:
        return bool(assigned_ids)
    return event.activity_id in assigned_ids if event.activity_id is not None else False


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "start_date must not exceed end_date")


@router.post(
    "/api/events",
    response_model=ConstructionEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_event(
    data: ConstructionEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConstructionEvent:
    project = db.get(Project, data.project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    activity = _activity(db, data.activity_id) if data.activity_id else None
    if activity is not None:
        if activity.project_id != data.project_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity must belong to the project")
        if not _can_access_activity(db, activity, current_user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    elif current_user.role not in MANAGEMENT_ROLES | {UserRole.SITE_ENGINEER}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "An activity is required for your role")
    if data.wbs_id is not None:
        wbs = db.get(WBS, data.wbs_id)
        if wbs is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "WBS not found")
        if wbs.project_id != data.project_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "WBS must belong to the project")
    if data.evidence_id is not None:
        evidence = db.get(Evidence, data.evidence_id)
        if evidence is None or evidence.project_id != data.project_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Evidence must belong to the project")
    event = create_event(
        db,
        project_id=data.project_id,
        activity_id=data.activity_id,
        wbs_id=data.wbs_id,
        event_type=data.event_type,
        actor_user_id=current_user.id,
        event_timestamp=data.event_timestamp,
        latitude=data.latitude,
        longitude=data.longitude,
        gps_accuracy=data.gps_accuracy,
        zone=data.zone,
        title=data.title,
        description=data.description,
        metadata=data.metadata,
        evidence_id=data.evidence_id,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
    )
    db.commit()
    return get_event(db, event.id) or event


@router.get(
    "/api/projects/{project_id}/events",
    response_model=ConstructionEventListResponse,
)
def list_project_events(
    project_id: int,
    event_type: ConstructionEventType | None = None,
    activity_id: int | None = Query(None, gt=0),
    wbs_id: int | None = Query(None, gt=0),
    actor_user_id: int | None = Query(None, gt=0),
    zone: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    _validate_date_range(start_date, end_date)
    activity_ids = None
    if current_user.role not in MANAGEMENT_ROLES:
        activity_ids = _assigned_activity_ids(db, current_user.id, project_id)
        if not activity_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project")
    items, total = get_project_events(
        db,
        project_id,
        event_type=event_type,
        activity_id=activity_id,
        wbs_id=wbs_id,
        actor_user_id=actor_user_id,
        zone=zone,
        start_date=start_date,
        end_date=end_date,
        activity_ids=activity_ids,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get(
    "/api/activities/{activity_id}/events",
    response_model=ConstructionEventListResponse,
)
def list_activity_event_history(
    activity_id: int,
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity = _activity(db, activity_id)
    if not _can_access_activity(db, activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    items, total = get_activity_events(
        db,
        activity_id,
        descending=sort == "desc",
        page=page,
        page_size=page_size,
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/api/events/{event_id}", response_model=ConstructionEventResponse)
def read_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConstructionEvent:
    event = get_event(db, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Construction event not found")
    if not _can_access_event(db, event, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized to view this event")
    return event


@router.get(
    "/api/projects/{project_id}/timeline",
    response_model=ProjectTimelineResponse,
)
def project_timeline(
    project_id: int,
    timeline_date: date | None = Query(None, alias="date"),
    start_date: date | None = None,
    end_date: date | None = None,
    event_type: ConstructionEventType | None = None,
    activity_id: int | None = Query(None, gt=0),
    zone: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    _validate_date_range(start_date, end_date)
    if timeline_date is not None and (start_date is not None or end_date is not None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date cannot be combined with start_date or end_date",
        )
    activity_ids = None
    if current_user.role not in MANAGEMENT_ROLES:
        activity_ids = _assigned_activity_ids(db, current_user.id, project_id)
        if not activity_ids:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You are not authorized for this project timeline",
            )
    resolved_start, resolved_end = resolve_project_range(
        db,
        project_id,
        timeline_date,
        start_date,
        end_date,
        event_type=event_type,
        activity_id=activity_id,
        zone=zone,
        activity_ids=activity_ids,
    )
    events, total = get_project_timeline(
        db,
        project_id,
        event_type=event_type,
        activity_id=activity_id,
        zone=zone,
        start_date=resolved_start,
        end_date=resolved_end,
        activity_ids=activity_ids,
        page=page,
        page_size=page_size,
    )
    return {
        "project_id": project_id,
        "date": timeline_date,
        "start_date": resolved_start,
        "end_date": resolved_end,
        "page": page,
        "page_size": page_size,
        "total": total,
        "events": events,
    }


@router.get(
    "/api/activities/{activity_id}/timeline",
    response_model=ActivityTimelineResponse,
)
def activity_timeline(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity = _activity(db, activity_id)
    if not _can_access_activity(db, activity, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized for this activity timeline",
        )
    activity_info, events = get_activity_timeline(db, activity_id)
    return {"activity": activity_info, "events": events}


@router.get(
    "/api/projects/{project_id}/timeline/daily-summary",
    response_model=DailySummaryResponse,
)
def project_daily_timeline_summary(
    project_id: int,
    summary_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailySummaryResponse:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    activity_ids = None
    if current_user.role not in MANAGEMENT_ROLES:
        activity_ids = _assigned_activity_ids(db, current_user.id, project_id)
        if not activity_ids:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You are not authorized for this project timeline",
            )
    return get_daily_summary(
        db,
        project_id,
        summary_date,
        activity_ids=activity_ids,
    )


@router.get(
    "/api/projects/{project_id}/replay",
    response_model=ReplayResponse,
)
def project_replay(
    project_id: int,
    replay_date: date = Query(..., alias="date"),
    start_time: str | None = None,
    end_time: str | None = None,
    event_type: ConstructionEventType | None = None,
    activity_id: int | None = Query(None, gt=0),
    zone: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReplayResponse:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    activity_ids = None
    if current_user.role not in MANAGEMENT_ROLES:
        activity_ids = _assigned_activity_ids(db, current_user.id, project_id)
        if not activity_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project replay")
    try:
        parsed_start = parse_replay_time(start_time)
        parsed_end = parse_replay_time(end_time)
        replay = build_replay(
            db,
            project_id=project_id,
            activity_id=activity_id,
            requested_date=replay_date,
            start_date=None,
            end_date=None,
            start_time=parsed_start,
            end_time=parsed_end,
            event_type=event_type,
            zone=zone,
            activity_ids=activity_ids,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc
    return replay


@router.get(
    "/api/activities/{activity_id}/replay",
    response_model=ReplayResponse,
)
def activity_replay(
    activity_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    event_type: ConstructionEventType | None = None,
    zone: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReplayResponse:
    activity = _activity(db, activity_id)
    if not _can_access_activity(db, activity, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity replay")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "start_date must not exceed end_date")
    try:
        parsed_start = parse_replay_time(start_time)
        parsed_end = parse_replay_time(end_time)
        return build_replay(
            db,
            project_id=activity.project_id,
            activity_id=activity_id,
            requested_date=None,
            start_date=start_date,
            end_date=end_date,
            start_time=parsed_start,
            end_time=parsed_end,
            event_type=event_type,
            zone=zone,
            activity_ids=None,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc
