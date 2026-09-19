from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.construction_event import ConstructionEvent, ConstructionEventType
from app.services.memory.memory_service import create_memory_from_event


def create_event(
    db: Session,
    *,
    project_id: int,
    event_type: ConstructionEventType,
    title: str,
    actor_user_id: int | None = None,
    activity_id: int | None = None,
    wbs_id: int | None = None,
    event_timestamp: datetime | None = None,
    latitude: Any = None,
    longitude: Any = None,
    gps_accuracy: Any = None,
    zone: str | None = None,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
    evidence_id: int | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> ConstructionEvent:
    query = select(ConstructionEvent).where(
        ConstructionEvent.project_id == project_id,
        ConstructionEvent.event_type == event_type,
        ConstructionEvent.reference_type == reference_type,
        ConstructionEvent.reference_id == reference_id,
    )
    if reference_type is not None and reference_id is not None:
        existing = db.scalar(query)
        if existing is not None:
            create_memory_from_event(db, existing)
            return existing
    event = ConstructionEvent(
        project_id=project_id,
        activity_id=activity_id,
        wbs_id=wbs_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        event_timestamp=event_timestamp or datetime.now(timezone.utc),
        latitude=latitude,
        longitude=longitude,
        gps_accuracy=gps_accuracy,
        zone=zone,
        title=title,
        description=description,
        event_metadata=metadata,
        evidence_id=evidence_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(event)
    db.flush()
    create_memory_from_event(db, event)
    return event


def _event_options():
    return (
        selectinload(ConstructionEvent.actor),
        selectinload(ConstructionEvent.activity),
        selectinload(ConstructionEvent.wbs),
        selectinload(ConstructionEvent.evidence),
    )


def get_event(db: Session, event_id: int) -> ConstructionEvent | None:
    return db.scalar(
        select(ConstructionEvent)
        .options(*_event_options())
        .where(ConstructionEvent.id == event_id)
    )


def _date_bounds(
    start_date: date | None, end_date: date | None
) -> tuple[datetime | None, datetime | None]:
    start = (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        if start_date
        else None
    )
    end = (
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        if end_date
        else None
    )
    return start, end


def get_project_events(
    db: Session,
    project_id: int,
    *,
    event_type: ConstructionEventType | None = None,
    activity_id: int | None = None,
    wbs_id: int | None = None,
    actor_user_id: int | None = None,
    zone: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    activity_ids: set[int] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ConstructionEvent], int]:
    query = select(ConstructionEvent).where(ConstructionEvent.project_id == project_id)
    if activity_ids is not None:
        query = query.where(ConstructionEvent.activity_id.in_(activity_ids))
    if event_type is not None:
        query = query.where(ConstructionEvent.event_type == event_type)
    if activity_id is not None:
        query = query.where(ConstructionEvent.activity_id == activity_id)
    if wbs_id is not None:
        query = query.where(ConstructionEvent.wbs_id == wbs_id)
    if actor_user_id is not None:
        query = query.where(ConstructionEvent.actor_user_id == actor_user_id)
    if zone is not None:
        query = query.where(ConstructionEvent.zone == zone)
    start, end = _date_bounds(start_date, end_date)
    if start is not None:
        query = query.where(ConstructionEvent.event_timestamp >= start)
    if end is not None:
        query = query.where(ConstructionEvent.event_timestamp < end)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    items = list(
        db.scalars(
            query.options(*_event_options())
            .order_by(ConstructionEvent.event_timestamp.desc(), ConstructionEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def get_activity_events(
    db: Session,
    activity_id: int,
    *,
    descending: bool = True,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[ConstructionEvent], int]:
    query = select(ConstructionEvent).where(ConstructionEvent.activity_id == activity_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    ordering = (
        ConstructionEvent.event_timestamp.desc()
        if descending
        else ConstructionEvent.event_timestamp.asc()
    )
    items = list(
        db.scalars(
            query.options(*_event_options())
            .order_by(ordering, ConstructionEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total
