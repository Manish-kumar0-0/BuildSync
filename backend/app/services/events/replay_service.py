from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.construction_event import ConstructionEvent, ConstructionEventType
from app.models.evidence import Evidence
from app.schemas.replay import (
    ReplayDuration,
    ReplayEvidenceReference,
    ReplayEvent,
    ReplayLocation,
    ReplayResponse,
    ReplaySummary,
)

MAX_REPLAY_EVENTS = 10_000
MAJOR_REPLAY_EVENTS = {
    ConstructionEventType.RISK_DETECTED,
    ConstructionEventType.DELAY_PREDICTED,
    ConstructionEventType.WEATHER_INTERRUPTION,
    ConstructionEventType.SAFETY_INCIDENT,
    ConstructionEventType.QUALITY_INSPECTION,
    ConstructionEventType.MILESTONE_MISSED,
    ConstructionEventType.RECOVERY_RECOMMENDED,
    ConstructionEventType.RECOVERY_ACCEPTED,
    ConstructionEventType.EVIDENCE_CAPTURED,
    ConstructionEventType.PROGRESS_REPORTED,
}


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _day_end(value: date) -> datetime:
    return _day_start(value + timedelta(days=1))


def parse_replay_time(value: str | None) -> time | None:
    if value is None:
        return None
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Time must use HH:MM or HH:MM:SS format") from exc
    if parsed.tzinfo is not None:
        raise ValueError("Replay times must not include a timezone")
    return parsed


def _window(
    requested_date: date | None,
    start_date: date | None,
    end_date: date | None,
    start_time: time | None,
    end_time: time | None,
) -> tuple[datetime | None, datetime | None]:
    if requested_date is not None:
        start = datetime.combine(requested_date, start_time or time.min, tzinfo=timezone.utc)
        end = datetime.combine(requested_date, end_time, tzinfo=timezone.utc) if end_time else _day_end(requested_date)
        if end_time is not None and end <= start:
            raise ValueError("end_time must be later than start_time")
        return start, end
    start = (
        datetime.combine(start_date, start_time or time.min, tzinfo=timezone.utc)
        if start_date
        else None
    )
    end = (
        datetime.combine(end_date, end_time, tzinfo=timezone.utc)
        if end_date and end_time
        else (_day_end(end_date) if end_date else None)
    )
    if start is not None and end is not None and end <= start:
        raise ValueError("Replay end must be later than replay start")
    return start, end


def _event_query(
    *,
    project_id: int | None,
    activity_id: int | None,
    event_type: ConstructionEventType | None,
    zone: str | None,
    start: datetime | None,
    end: datetime | None,
    activity_ids: set[int] | None,
):
    query = (
        select(ConstructionEvent, Evidence)
        .outerjoin(Evidence, Evidence.id == ConstructionEvent.evidence_id)
    )
    if project_id is not None:
        query = query.where(ConstructionEvent.project_id == project_id)
    if activity_id is not None:
        query = query.where(ConstructionEvent.activity_id == activity_id)
    if activity_ids is not None:
        query = query.where(ConstructionEvent.activity_id.in_(activity_ids))
    if event_type is not None:
        query = query.where(ConstructionEvent.event_type == event_type)
    if zone is not None:
        query = query.where(ConstructionEvent.zone == zone)
    if start is not None:
        query = query.where(ConstructionEvent.event_timestamp >= start)
    if end is not None:
        query = query.where(ConstructionEvent.event_timestamp < end)
    return query.order_by(ConstructionEvent.event_timestamp.asc(), ConstructionEvent.id.asc())


def _to_replay_event(
    event: ConstructionEvent,
    evidence: Evidence | None,
    first_timestamp: datetime,
    sequence: int,
) -> ReplayEvent:
    timestamp = event.event_timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    location = None
    if event.latitude is not None and event.longitude is not None:
        location = ReplayLocation(
            latitude=event.latitude,
            longitude=event.longitude,
            gps_accuracy=event.gps_accuracy,
        )
    evidence_reference = None
    if evidence is not None:
        evidence_reference = ReplayEvidenceReference(
            evidence_id=evidence.id,
            file_type=evidence.mime_type,
            captured_at=evidence.captured_at,
        )
    return ReplayEvent(
        sequence=sequence,
        event_id=event.id,
        timestamp=timestamp,
        relative_time_seconds=max(0, int((timestamp - first_timestamp).total_seconds())),
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        activity_id=event.activity_id,
        zone=event.zone,
        location=location,
        evidence_id=event.evidence_id,
        evidence=evidence_reference,
        metadata=event.event_metadata,
        is_major_event=event.event_type in MAJOR_REPLAY_EVENTS,
    )


def build_replay(
    db: Session,
    *,
    project_id: int | None,
    activity_id: int | None,
    requested_date: date | None,
    start_date: date | None,
    end_date: date | None,
    start_time: time | None,
    end_time: time | None,
    event_type: ConstructionEventType | None,
    zone: str | None,
    activity_ids: set[int] | None,
) -> ReplayResponse:
    start, end = _window(
        requested_date, start_date, end_date, start_time, end_time
    )
    query = _event_query(
        project_id=project_id,
        activity_id=activity_id,
        event_type=event_type,
        zone=zone,
        start=start,
        end=end,
        activity_ids=activity_ids,
    )
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    if total > MAX_REPLAY_EVENTS:
        raise OverflowError(
            f"Replay contains {total} events, exceeding the maximum of "
            f"{MAX_REPLAY_EVENTS}. Narrow the requested time window."
        )
    rows = db.execute(query).all()
    events = []
    if rows:
        first_timestamp = rows[0][0].event_timestamp
        if first_timestamp.tzinfo is None:
            first_timestamp = first_timestamp.replace(tzinfo=timezone.utc)
        events = [
            _to_replay_event(event, evidence, first_timestamp, index)
            for index, (event, evidence) in enumerate(rows, start=1)
        ]
    first = events[0].timestamp if events else None
    last = events[-1].timestamp if events else None
    major_count = sum(event.is_major_event for event in events)
    summary = ReplaySummary(
        total_events=total,
        first_event=first.astimezone(timezone.utc).strftime("%H:%M") if first else None,
        last_event=last.astimezone(timezone.utc).strftime("%H:%M") if last else None,
        activities_involved=len({event.activity_id for event in events if event.activity_id}),
        zones_involved=len({event.zone for event in events if event.zone}),
        major_events=major_count,
        weather_interruptions=sum(
            event.event_type == ConstructionEventType.WEATHER_INTERRUPTION for event in events
        ),
        risks_detected=sum(
            event.event_type == ConstructionEventType.RISK_DETECTED for event in events
        ),
        delays_predicted=sum(
            event.event_type == ConstructionEventType.DELAY_PREDICTED for event in events
        ),
    )
    return ReplayResponse(
        project_id=project_id or 0,
        date=requested_date,
        duration=ReplayDuration(
            start=first.astimezone(timezone.utc).strftime("%H:%M") if first else None,
            end=last.astimezone(timezone.utc).strftime("%H:%M") if last else None,
        ),
        total_events=total,
        events=events,
        summary=summary,
    )
