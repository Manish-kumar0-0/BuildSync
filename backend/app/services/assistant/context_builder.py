from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.construction_event import ConstructionEvent
from app.models.field_activity import Activity
from app.models.planning import Project
from app.models.project_memory import ProjectMemory
from app.models.progress_assessment import ProgressAssessment
from app.models.recovery import RecoveryRecommendation
from app.models.risk_prediction import ActivityRiskPrediction
from app.models.evidence import Evidence
from app.models.resource_tracking import Equipment, EquipmentIssue, MaterialItem
from app.models.site_disruption import SiteDisruption
from app.models.safety import SafetyIncident
from app.models.quality import QualityDefect, QualityInspection
from app.models.workforce import AttendanceRecord, AttendanceStatus, WorkerAssignment, WorkforceAssignmentStatus
from app.models.notification import Notification
from app.schemas.assistant import AssistantContext, AssistantSource

INTENTS = (
    "PROGRESS",
    "DELAY",
    "RISK",
    "RECOVERY",
    "TIMELINE",
    "MEMORY",
    "ACTIVITY",
    "EVIDENCE",
    "WORKFORCE",
    "MATERIAL",
    "EQUIPMENT",
    "SAFETY",
    "QUALITY",
    "WEATHER",
    "PROJECT",
    "GENERAL_PROJECT",
)


def detect_intent(question: str) -> str:
    text = question.casefold()
    if any(word in text for word in ("material", "steel", "stock", "inventory")):
        return "MATERIAL"
    if any(word in text for word in ("equipment", "machine", "unavailable", "maintenance")):
        return "EQUIPMENT"
    if any(word in text for word in ("safety", "incident", "hazard", "near miss", "ppe")):
        return "SAFETY"
    if any(word in text for word in ("quality", "defect", "inspection", "qa", "qc")):
        return "QUALITY"
    if any(word in text for word in ("worker", "workforce", "attendance", "present", "crew")):
        return "WORKFORCE"
    if any(word in text for word in ("evidence", "photo", "proof", "verification")):
        return "EVIDENCE"
    if any(word in text for word in ("weather", "rain", "storm", "wind", "heat")):
        return "WEATHER"
    if any(word in text for word in ("project status", "project summary", "project overview")):
        return "PROJECT"
    if any(word in text for word in ("risk", "critical", "danger")):
        return "RISK"
    if any(word in text for word in ("recover", "recommend", "action", "mitigat")):
        return "RECOVERY"
    if any(word in text for word in ("delay", "late", "behind", "slip")):
        return "DELAY"
    if any(word in text for word in ("progress", "complete", "completed", "variance")):
        return "PROGRESS"
    if any(word in text for word in ("happened", "yesterday", "today", "timeline", "when")):
        return "TIMELINE"
    if any(word in text for word in ("history", "before", "previous", "memory")):
        return "MEMORY"
    if any(word in text for word in ("activity", "activities", "task", "tasks")):
        return "ACTIVITY"
    return "GENERAL_PROJECT"


def _source(
    sources: list[AssistantSource], source_type: str, source_id: int
) -> None:
    reference = AssistantSource(type=source_type, id=source_id)
    if reference not in sources:
        sources.append(reference)


def _decimal(value: Any) -> Any:
    return float(value) if value is not None else None


def _date_window(question: str) -> tuple[datetime | None, datetime | None]:
    text = question.casefold()
    if "yesterday" in text:
        end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return end - timedelta(days=1), end
    if "today" in text:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)
    return None, None


def build_project_context(
    db: Session,
    project_id: int,
    question: str,
    activity_id: int | None = None,
) -> AssistantContext:
    intent = detect_intent(question)
    sources: list[AssistantSource] = []
    records: list[dict[str, Any]] = []
    project = db.get(Project, project_id)
    if project is not None:
        records.append(
            {
                "type": "Project",
                "id": project.id,
                "name": project.name,
                "status": project.status.value,
                "location": project.location,
                "planned_end_date": project.planned_end_date.isoformat(),
            }
        )
    activity_filter = (
        (ProgressAssessment.activity_id == activity_id)
        if activity_id is not None
        else True
    )

    activities = list(
        db.scalars(
            select(Activity)
            .where(Activity.project_id == project_id)
            .where(Activity.id == activity_id if activity_id is not None else True)
            .order_by(Activity.updated_at.desc())
            .limit(10)
        ).all()
    )
    for activity in activities:
        _source(sources, "Activity", activity.id)
        records.append(
            {
                "type": "Activity",
                "id": activity.id,
                "name": activity.name,
                "status": activity.status.value,
                "reported_progress": _decimal(activity.progress_percentage),
                "zone": activity.zone,
            }
        )

    if intent in {"EVIDENCE", "ACTIVITY", "DELAY", "GENERAL_PROJECT"}:
        evidence_query = select(Evidence).where(Evidence.project_id == project_id)
        if activity_id is not None:
            evidence_query = evidence_query.where(Evidence.activity_id == activity_id)
        for evidence in db.scalars(evidence_query.order_by(Evidence.created_at.desc()).limit(10)).all():
            _source(sources, "Evidence", evidence.id)
            records.append({
                "type": "Evidence", "id": evidence.id, "activity_id": evidence.activity_id,
                "status": evidence.status.value, "captured_at": evidence.captured_at.isoformat()
                if evidence.captured_at else None,
            })

    if intent in {"DELAY", "WEATHER", "GENERAL_PROJECT"}:
        disruption_query = select(SiteDisruption).where(SiteDisruption.project_id == project_id)
        if activity_id is not None:
            disruption_query = disruption_query.where(SiteDisruption.activity_id == activity_id)
        for disruption in db.scalars(disruption_query.order_by(SiteDisruption.start_time.desc()).limit(10)).all():
            _source(sources, "SiteDisruption", disruption.id)
            records.append({
                "type": "SiteDisruption", "id": disruption.id, "activity_id": disruption.activity_id,
                "type_name": disruption.type.value, "severity": disruption.severity.value,
                "start_time": disruption.start_time.isoformat(), "duration_minutes": disruption.duration_minutes,
                "zone": disruption.zone, "description": disruption.description,
            })

    if intent in {"MATERIAL", "GENERAL_PROJECT"}:
        for item in db.scalars(select(MaterialItem).where(MaterialItem.project_id == project_id).limit(20)).all():
            _source(sources, "MaterialItem", item.id)
            records.append({"type": "MaterialItem", "id": item.id, "name": item.name,
                            "quantity": _decimal(item.current_quantity), "minimum": _decimal(item.minimum_stock_level),
                            "unit": item.unit})

    if intent in {"EQUIPMENT", "GENERAL_PROJECT"}:
        for item in db.scalars(select(Equipment).where(Equipment.project_id == project_id).limit(20)).all():
            _source(sources, "Equipment", item.id)
            records.append({"type": "Equipment", "id": item.id, "name": item.name,
                            "status": item.status.value})
        for issue in db.scalars(select(EquipmentIssue).where(EquipmentIssue.project_id == project_id).order_by(EquipmentIssue.reported_at.desc()).limit(10)).all():
            _source(sources, "EquipmentIssue", issue.id)
            records.append({"type": "EquipmentIssue", "id": issue.id, "equipment_id": issue.equipment_id,
                            "severity": issue.severity.value, "description": issue.description})

    if intent in {"SAFETY", "GENERAL_PROJECT"}:
        for incident in db.scalars(select(SafetyIncident).where(SafetyIncident.project_id == project_id).order_by(SafetyIncident.occurred_at.desc()).limit(20)).all():
            _source(sources, "SafetyIncident", incident.id)
            records.append({"type": "SafetyIncident", "id": incident.id, "severity": incident.severity.value,
                            "status": incident.status.value, "description": incident.description, "zone": incident.zone})

    if intent in {"QUALITY", "GENERAL_PROJECT"}:
        for inspection in db.scalars(select(QualityInspection).where(QualityInspection.project_id == project_id).order_by(QualityInspection.inspected_at.desc()).limit(10)).all():
            _source(sources, "QualityInspection", inspection.id)
            records.append({"type": "QualityInspection", "id": inspection.id, "status": inspection.status.value,
                            "score": _decimal(inspection.score), "notes": inspection.notes})
        for defect in db.scalars(select(QualityDefect).where(QualityDefect.project_id == project_id).order_by(QualityDefect.created_at.desc()).limit(10)).all():
            _source(sources, "QualityDefect", defect.id)
            records.append({"type": "QualityDefect", "id": defect.id, "severity": defect.severity.value,
                            "status": defect.status.value, "description": defect.description})

    if intent in {"WORKFORCE", "GENERAL_PROJECT"}:
        worker_count = db.query(WorkerAssignment).filter(
            WorkerAssignment.project_id == project_id,
            WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE,
        ).count()
        present = db.query(AttendanceRecord).filter(
            AttendanceRecord.project_id == project_id,
            AttendanceRecord.attendance_date == datetime.now(timezone.utc).date(),
            AttendanceRecord.status == AttendanceStatus.PRESENT,
        ).count()
        records.append({"type": "WorkforceSummary", "active_assignments": worker_count, "present_today": present})

    if intent in {"PROJECT", "GENERAL_PROJECT"}:
        unread = db.query(Notification).filter(
            Notification.project_id == project_id, Notification.is_read.is_(False)
        ).count()
        records.append({"type": "NotificationSummary", "unread": unread})

    assessments = list(
        db.scalars(
            select(ProgressAssessment)
            .options(selectinload(ProgressAssessment.activity))
            .where(
                ProgressAssessment.project_id == project_id,
                activity_filter,
            )
            .order_by(
                ProgressAssessment.assessment_date.desc(),
                ProgressAssessment.id.desc(),
            )
            .limit(10)
        ).all()
    )
    for assessment in assessments:
        _source(sources, "ProgressAssessment", assessment.id)
        records.append(
            {
                "type": "ProgressAssessment",
                "id": assessment.id,
                "activity_id": assessment.activity_id,
                "activity": assessment.activity.name if assessment.activity else None,
                "date": assessment.assessment_date.isoformat(),
                "planned_progress": _decimal(assessment.planned_progress),
                "reported_progress": _decimal(assessment.reported_progress),
                "ai_estimated_progress": _decimal(assessment.ai_estimated_progress),
                "ai_confidence": _decimal(assessment.ai_confidence),
                "fused_progress": _decimal(assessment.fused_progress),
                "variance_from_plan": _decimal(assessment.variance_from_plan),
                "status": assessment.assessment_status.value,
            }
        )

    predictions = list(
        db.scalars(
            select(ActivityRiskPrediction)
            .options(selectinload(ActivityRiskPrediction.activity))
            .where(
                ActivityRiskPrediction.project_id == project_id,
                (
                    ActivityRiskPrediction.activity_id == activity_id
                    if activity_id is not None
                    else True
                ),
            )
            .order_by(
                ActivityRiskPrediction.prediction_date.desc(),
                ActivityRiskPrediction.id.desc(),
            )
            .limit(10)
        ).all()
    )
    for prediction in predictions:
        _source(sources, "ActivityRiskPrediction", prediction.id)
        records.append(
            {
                "type": "ActivityRiskPrediction",
                "id": prediction.id,
                "activity_id": prediction.activity_id,
                "activity": prediction.activity.name if prediction.activity else None,
                "date": prediction.prediction_date.isoformat(),
                "risk_level": prediction.risk_level.value,
                "risk_score": _decimal(prediction.risk_score),
                "primary_risk": prediction.primary_risk.value,
                "predicted_delay_days": _decimal(prediction.predicted_delay_days),
                "confidence_score": _decimal(prediction.confidence_score),
                "risk_factors": prediction.risk_factors,
                "explanation": prediction.explanation,
            }
        )

    recommendations = list(
        db.scalars(
            select(RecoveryRecommendation)
            .options(selectinload(RecoveryRecommendation.activity))
            .where(
                RecoveryRecommendation.project_id == project_id,
                (
                    RecoveryRecommendation.activity_id == activity_id
                    if activity_id is not None
                    else True
                ),
            )
            .order_by(RecoveryRecommendation.created_at.desc())
            .limit(10)
        ).all()
    )
    for recommendation in recommendations:
        _source(sources, "RecoveryRecommendation", recommendation.id)
        records.append(
            {
                "type": "RecoveryRecommendation",
                "id": recommendation.id,
                "activity_id": recommendation.activity_id,
                "activity": recommendation.activity.name if recommendation.activity else None,
                "title": recommendation.title,
                "description": recommendation.description,
                "priority": recommendation.priority.value,
                "status": recommendation.status.value,
                "expected_impact": recommendation.expected_impact.value,
            }
        )

    start_time, end_time = _date_window(question)
    event_query = (
        select(ConstructionEvent)
        .where(ConstructionEvent.project_id == project_id)
        .order_by(ConstructionEvent.event_timestamp.desc())
        .limit(20)
    )
    if activity_id is not None:
        event_query = event_query.where(ConstructionEvent.activity_id == activity_id)
    if start_time is not None:
        event_query = event_query.where(ConstructionEvent.event_timestamp >= start_time)
        event_query = event_query.where(ConstructionEvent.event_timestamp < end_time)
    events = list(db.scalars(event_query).all())
    for event in events:
        _source(sources, "ConstructionEvent", event.id)
        records.append(
            {
                "type": "ConstructionEvent",
                "id": event.id,
                "event_type": event.event_type.value,
                "timestamp": event.event_timestamp.isoformat(),
                "title": event.title,
                "description": event.description,
                "activity_id": event.activity_id,
                "zone": event.zone,
                "evidence_id": event.evidence_id,
                "metadata": event.event_metadata,
            }
        )

    memory_query = (
        select(ProjectMemory)
        .where(ProjectMemory.project_id == project_id)
        .order_by(ProjectMemory.memory_date.desc(), ProjectMemory.id.desc())
        .limit(20)
    )
    if activity_id is not None:
        memory_query = memory_query.where(ProjectMemory.activity_id == activity_id)
    memories = list(db.scalars(memory_query).all())
    for memory in memories:
        _source(sources, "ProjectMemory", memory.id)
        records.append(
            {
                "type": "ProjectMemory",
                "id": memory.id,
                "date": memory.memory_date.isoformat(),
                "activity_id": memory.activity_id,
                "memory_type": memory.memory_type.value,
                "importance": memory.importance.value,
                "title": memory.title,
                "summary": memory.summary,
            }
        )

    return AssistantContext(
        project_id=project_id,
        intent=intent,
        question=question,
        records=records,
        sources=sources,
    )
