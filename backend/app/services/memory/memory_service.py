from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.construction_event import ConstructionEvent, ConstructionEventType
from app.models.project_memory import MemoryImportance, MemoryType, ProjectMemory

MEMORY_EVENT_TYPES: dict[ConstructionEventType, MemoryType] = {
    ConstructionEventType.PROGRESS_REPORTED: MemoryType.PROGRESS,
    ConstructionEventType.PROGRESS_ASSESSED: MemoryType.PROGRESS,
    ConstructionEventType.RISK_DETECTED: MemoryType.RISK,
    ConstructionEventType.DELAY_PREDICTED: MemoryType.DELAY,
    ConstructionEventType.RECOVERY_RECOMMENDED: MemoryType.RECOVERY,
    ConstructionEventType.RECOVERY_ACCEPTED: MemoryType.RECOVERY,
    ConstructionEventType.RECOVERY_IMPLEMENTED: MemoryType.RECOVERY,
    ConstructionEventType.WEATHER_INTERRUPTION: MemoryType.WEATHER,
    ConstructionEventType.SAFETY_INCIDENT: MemoryType.SAFETY,
    ConstructionEventType.QUALITY_INSPECTION_FAILED: MemoryType.QUALITY,
    ConstructionEventType.QUALITY_DEFECT: MemoryType.QUALITY,
    ConstructionEventType.MATERIAL_RECEIVED: MemoryType.MATERIAL,
    ConstructionEventType.MATERIAL_DISPATCHED: MemoryType.MATERIAL,
    ConstructionEventType.EQUIPMENT_ISSUE: MemoryType.EQUIPMENT,
    ConstructionEventType.WORKFORCE_ASSIGNED: MemoryType.WORKFORCE,
    ConstructionEventType.WORKFORCE_UNASSIGNED: MemoryType.WORKFORCE,
    ConstructionEventType.ATTENDANCE_CHECK_IN: MemoryType.WORKFORCE,
    ConstructionEventType.ATTENDANCE_CHECK_OUT: MemoryType.WORKFORCE,
    ConstructionEventType.MILESTONE_MISSED: MemoryType.MILESTONE,
    ConstructionEventType.EVIDENCE_REJECTED: MemoryType.EVIDENCE,
    ConstructionEventType.EVIDENCE_COMPARISON_COMPLETED: MemoryType.EVIDENCE,
    ConstructionEventType.MATERIAL_RECEIVED: MemoryType.MATERIAL,
    ConstructionEventType.MATERIAL_DISPATCHED: MemoryType.MATERIAL,
    ConstructionEventType.EQUIPMENT_ISSUE: MemoryType.EQUIPMENT,
}


def _importance(event: ConstructionEvent) -> MemoryImportance:
    if event.event_type == ConstructionEventType.RISK_DETECTED:
        risk_level = (event.event_metadata or {}).get("risk_level")
        if risk_level == "CRITICAL":
            return MemoryImportance.CRITICAL
        if risk_level == "HIGH":
            return MemoryImportance.HIGH
        return MemoryImportance.MEDIUM
    if event.event_type in {
        ConstructionEventType.SAFETY_INCIDENT,
        ConstructionEventType.QUALITY_INSPECTION_FAILED,
        ConstructionEventType.QUALITY_DEFECT,
        ConstructionEventType.MILESTONE_MISSED,
        ConstructionEventType.DELAY_PREDICTED,
    }:
        return MemoryImportance.HIGH
    if event.event_type in {
        ConstructionEventType.WEATHER_INTERRUPTION,
        ConstructionEventType.QUALITY_INSPECTION,
        ConstructionEventType.RECOVERY_RECOMMENDED,
        ConstructionEventType.RECOVERY_ACCEPTED,
        ConstructionEventType.RECOVERY_IMPLEMENTED,
        ConstructionEventType.EVIDENCE_REJECTED,
        ConstructionEventType.EQUIPMENT_ISSUE,
    }:
        return MemoryImportance.MEDIUM
    return MemoryImportance.LOW


def _activity_name(event: ConstructionEvent) -> str:
    return event.activity.name if event.activity is not None else "Project"


def _summary(event: ConstructionEvent) -> str:
    metadata = event.event_metadata or {}
    activity_name = _activity_name(event)
    if event.event_type == ConstructionEventType.PROGRESS_REPORTED:
        progress = metadata.get("progress_percentage", metadata.get("reported_progress"))
        return f"Reported progress reached {progress}% for {activity_name}."
    if event.event_type == ConstructionEventType.PROGRESS_ASSESSED:
        progress = metadata.get("fused_progress")
        return f"Progress was assessed at {progress}% for {activity_name}."
    if event.event_type == ConstructionEventType.WEATHER_INTERRUPTION:
        description = event.description or "Recorded weather conditions interrupted construction."
        duration = metadata.get("duration_minutes")
        if duration is not None:
            return f"{description} Duration: approximately {duration} minutes."
        return description
    if event.event_type in {
        ConstructionEventType.MATERIAL_RECEIVED,
        ConstructionEventType.MATERIAL_DISPATCHED,
    }:
        quantity = metadata.get("quantity", "some")
        unit = metadata.get("unit", "")
        return f"{quantity} {unit} of {metadata.get('material_name', 'material')} was recorded."
    if event.event_type == ConstructionEventType.EQUIPMENT_ISSUE:
        return event.description or event.title
    if event.event_type == ConstructionEventType.DELAY_PREDICTED:
        delay = metadata.get("predicted_delay_days", "an estimated delay")
        return f"{activity_name} has {delay} predicted delay days."
    if event.event_type == ConstructionEventType.RISK_DETECTED:
        level = metadata.get("risk_level", "elevated")
        return f"{activity_name} risk was detected at {level}."
    if event.event_type == ConstructionEventType.EVIDENCE_COMPARISON_COMPLETED:
        return event.description or event.title
    if event.event_type in {
        ConstructionEventType.WORKFORCE_ASSIGNED,
        ConstructionEventType.WORKFORCE_UNASSIGNED,
        ConstructionEventType.ATTENDANCE_CHECK_IN,
        ConstructionEventType.ATTENDANCE_CHECK_OUT,
    }:
        return event.description or event.title
    return event.description or event.title


def create_memory_from_event(
    db: Session, event: ConstructionEvent
) -> ProjectMemory | None:
    if event.event_type == ConstructionEventType.SAFETY_INCIDENT and not (
        event.event_metadata or {}
    ).get("create_memory", False):
        return None
    if (
        event.event_type == ConstructionEventType.WEATHER_INTERRUPTION
        and (event.event_metadata or {}).get("severity") == "LOW"
    ):
        return None
    memory_type = MEMORY_EVENT_TYPES.get(event.event_type)
    if memory_type is None:
        return None
    existing = db.scalar(
        select(ProjectMemory).where(ProjectMemory.event_id == event.id)
    )
    if existing is not None:
        return existing
    event_date = event.event_timestamp.date()
    memory = ProjectMemory(
        project_id=event.project_id,
        event_id=event.id,
        activity_id=event.activity_id,
        memory_type=memory_type,
        title=event.title,
        summary=_summary(event),
        importance=_importance(event),
        memory_date=event_date,
        source_type="ConstructionEvent",
        source_id=event.id,
        event_metadata=event.event_metadata,
    )
    db.add(memory)
    db.flush()
    return memory
