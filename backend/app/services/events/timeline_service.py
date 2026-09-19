from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.construction_event import ConstructionEvent, ConstructionEventType
from app.models.field_activity import Activity
from app.models.user import User

from app.schemas.timeline import (
    DailySummaryResponse,
    MajorTimelineEvent,
    TimelineActivity,
    TimelineActor,
    TimelineEvent,
    TimelineLocation,
)

MAJOR_EVENT_TYPES = {
    ConstructionEventType.RISK_DETECTED,
    ConstructionEventType.DELAY_PREDICTED,
    ConstructionEventType.WEATHER_INTERRUPTION,
    ConstructionEventType.SAFETY_INCIDENT,
    ConstructionEventType.QUALITY_INSPECTION,
    ConstructionEventType.MILESTONE_MISSED,
    ConstructionEventType.RECOVERY_RECOMMENDED,
    ConstructionEventType.RECOVERY_ACCEPTED,
}


def _utc_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _utc_end(value: date) -> datetime:
    return _utc_start(value + timedelta(days=1))


def _event_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%H:%M")


def _timeline_columns():
    return (
        ConstructionEvent.id,
        ConstructionEvent.event_timestamp,
        ConstructionEvent.event_type,
        ConstructionEvent.title,
        ConstructionEvent.description,
        ConstructionEvent.activity_id,
        ConstructionEvent.zone,
        ConstructionEvent.latitude,
        ConstructionEvent.longitude,
        ConstructionEvent.gps_accuracy,
        User.id.label("actor_id"),
        User.full_name.label("actor_name"),
    )


def _timeline_query(project_id: int):
    return (
        select(*_timeline_columns())
        .outerjoin(User, User.id == ConstructionEvent.actor_user_id)
        .where(ConstructionEvent.project_id == project_id)
    )


def _to_timeline_event(row) -> TimelineEvent:
    actor = (
        TimelineActor(id=row.actor_id, name=row.actor_name)
        if row.actor_id is not None
        else None
    )
    return TimelineEvent(
        id=row.id,
        time=_event_time(row.event_timestamp),
        event_type=row.event_type,
        title=row.title,
        description=row.description,
        actor=actor,
        activity_id=row.activity_id,
        zone=row.zone,
        location=TimelineLocation(
            latitude=row.latitude,
            longitude=row.longitude,
            gps_accuracy=row.gps_accuracy,
        ),
    )


def resolve_project_range(
    db: Session,
    project_id: int,
    requested_date: date | None,
    start_date: date | None,
    end_date: date | None,
    *,
    event_type: ConstructionEventType | None = None,
    activity_id: int | None = None,
    zone: str | None = None,
    activity_ids: set[int] | None = None,
) -> tuple[date | None, date | None]:
    if requested_date is not None:
        return requested_date, requested_date
    if start_date is not None or end_date is not None:
        return start_date, end_date
    latest_query = select(func.max(ConstructionEvent.event_timestamp)).where(
        ConstructionEvent.project_id == project_id
    )
    if event_type is not None:
        latest_query = latest_query.where(ConstructionEvent.event_type == event_type)
    if activity_id is not None:
        latest_query = latest_query.where(ConstructionEvent.activity_id == activity_id)
    if zone is not None:
        latest_query = latest_query.where(ConstructionEvent.zone == zone)
    if activity_ids is not None:
        latest_query = latest_query.where(ConstructionEvent.activity_id.in_(activity_ids))
    latest = db.scalar(latest_query)
    if latest is None:
        return None, None
    latest_date = latest.date()
    return latest_date - timedelta(days=6), latest_date


def get_project_timeline(
    db: Session,
    project_id: int,
    *,
    event_type: ConstructionEventType | None,
    activity_id: int | None,
    zone: str | None,
    start_date: date | None,
    end_date: date | None,
    activity_ids: set[int] | None,
    page: int,
    page_size: int,
) -> tuple[list[TimelineEvent], int]:
    query = _timeline_query(project_id)
    if activity_ids is not None:
        query = query.where(ConstructionEvent.activity_id.in_(activity_ids))
    if event_type is not None:
        query = query.where(ConstructionEvent.event_type == event_type)
    if activity_id is not None:
        query = query.where(ConstructionEvent.activity_id == activity_id)
    if zone is not None:
        query = query.where(ConstructionEvent.zone == zone)
    if start_date is not None:
        query = query.where(ConstructionEvent.event_timestamp >= _utc_start(start_date))
    if end_date is not None:
        query = query.where(ConstructionEvent.event_timestamp < _utc_end(end_date))
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    rows = db.execute(
        query.order_by(
            ConstructionEvent.event_timestamp.asc(), ConstructionEvent.id.asc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [_to_timeline_event(row) for row in rows], total


def get_activity_timeline(
    db: Session, activity_id: int
) -> tuple[TimelineActivity, list[TimelineEvent]]:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise ValueError("Activity not found")
    rows = db.execute(
        _timeline_query(activity.project_id)
        .where(ConstructionEvent.activity_id == activity_id)
        .order_by(ConstructionEvent.event_timestamp.asc(), ConstructionEvent.id.asc())
    ).all()
    return TimelineActivity(id=activity.id, name=activity.name), [
        _to_timeline_event(row) for row in rows
    ]


def get_daily_summary(
    db: Session,
    project_id: int,
    summary_date: date,
    *,
    activity_ids: set[int] | None,
) -> DailySummaryResponse:
    query = _timeline_query(project_id).where(
        ConstructionEvent.event_timestamp >= _utc_start(summary_date),
        ConstructionEvent.event_timestamp < _utc_end(summary_date),
    )
    if activity_ids is not None:
        query = query.where(ConstructionEvent.activity_id.in_(activity_ids))
    rows = db.execute(
        query.order_by(ConstructionEvent.event_timestamp.asc(), ConstructionEvent.id.asc())
    ).all()
    events = [_to_timeline_event(row) for row in rows]
    counts = Counter(event.event_type.value for event in events)
    active_activity_ids = {event.activity_id for event in events if event.activity_id}
    completed_activity_ids = {
        event.activity_id
        for event in events
        if event.activity_id and event.event_type == ConstructionEventType.WORK_COMPLETED
    }
    major_events = [
        MajorTimelineEvent(
            event_id=event.id,
            time=event.time,
            type=event.event_type,
            title=event.title,
        )
        for event in events
        if event.event_type in MAJOR_EVENT_TYPES
    ]
    return DailySummaryResponse(
        date=summary_date,
        total_events=len(events),
        event_counts=dict(counts),
        zones_active=sorted({event.zone for event in events if event.zone}),
        activities_active=len(active_activity_ids),
        activities_completed=len(completed_activity_ids),
        major_events=major_events,
    )
