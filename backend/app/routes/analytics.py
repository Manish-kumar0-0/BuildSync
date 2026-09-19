from collections import Counter
from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import (
    Activity, ActivityAssignment, ActivityRiskPrediction, AssignmentStatus,
    AttendanceRecord, AttendanceStatus, Crew, Evidence,
    EvidenceComparisonAnalysis, EvidenceStatus, Equipment, EquipmentIssue,
    EquipmentStatus, MaterialItem, MaterialMovement,
    Project, ProjectUserAssignment, ProjectAssignmentStatus, ProgressAssessment,
    QualityDefect, QualityDefectStatus, QualityInspection, InspectionStatus,
    RiskLevel, RiskPredictionStatus, SafetyIncident, SafetyIncidentSeverity, SafetyIncidentStatus,
    SiteDisruption, User, UserRole, WorkerAssignment, WorkforceAssignmentStatus,
    ConstructionEvent, EquipmentUsageRecord, PPEInspection, ScheduleActivity,
    ScheduleApprovalStatus,
)
router = APIRouter(prefix="/api/projects/{project_id}/analytics", tags=["analytics"])
PROJECT_WIDE = {UserRole.ADMIN, UserRole.PROJECT_MANAGER}
PROJECT_ROLES = PROJECT_WIDE | {
    UserRole.SITE_ENGINEER, UserRole.FIELD_ENGINEER, UserRole.SAFETY_OFFICER,
    UserRole.QA_QC_ENGINEER, UserRole.FOREMAN,
}


def _access(db: Session, project_id: int, user: User) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "Project not found")
    if user.role in PROJECT_WIDE:
        return
    assigned = db.scalar(select(ProjectUserAssignment.id).where(
        ProjectUserAssignment.project_id == project_id,
        ProjectUserAssignment.user_id == user.id,
        ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE,
    ))
    activity_assigned = db.scalar(select(ActivityAssignment.id).join(
        Activity, Activity.id == ActivityAssignment.activity_id
    ).where(
        Activity.project_id == project_id,
        ActivityAssignment.user_id == user.id,
        ActivityAssignment.status == AssignmentStatus.ACTIVE,
    ))
    if user.role not in PROJECT_ROLES or assigned is None and activity_assigned is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for project analytics")


def _range(start_date: date | None, end_date: date | None) -> tuple[date | None, date | None]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must not exceed end_date")
    return start_date, end_date


def _date_filter(query, column, start: date | None, end: date | None):
    if start:
        query = query.where(column >= start)
    if end:
        query = query.where(column <= end)
    return query


def _latest_progress(items: list[ProgressAssessment]) -> dict[int, ProgressAssessment]:
    latest: dict[int, ProgressAssessment] = {}
    for item in items:
        if item.activity_id not in latest or (item.assessment_date, item.id) > (
            latest[item.activity_id].assessment_date, latest[item.activity_id].id
        ):
            latest[item.activity_id] = item
    return latest


def _latest_risk(items: list[ActivityRiskPrediction]) -> dict[int, ActivityRiskPrediction]:
    latest: dict[int, ActivityRiskPrediction] = {}
    for item in items:
        if item.activity_id not in latest or (item.prediction_date, item.id) > (
            latest[item.activity_id].prediction_date, latest[item.activity_id].id
        ):
            latest[item.activity_id] = item
    return latest


def _progress_rows(db: Session, project_id: int, zone: str | None, start: date | None, end: date | None):
    activities = list(db.scalars(select(Activity).where(
        Activity.project_id == project_id,
        Activity.zone == zone if zone else True,
    )).all())
    activity_ids = {item.id for item in activities}
    query = _date_filter(select(ProgressAssessment).where(
        ProgressAssessment.project_id == project_id,
        ProgressAssessment.activity_id.in_(activity_ids) if activity_ids else False,
    ), ProgressAssessment.assessment_date, start, end)
    assessments = _latest_progress(list(db.scalars(query).all()))
    rows = []
    for activity in activities:
        item = assessments.get(activity.id)
        planned = item.planned_progress if item else None
        actual = item.fused_progress if item and item.fused_progress is not None else (
            item.reported_progress if item else None
        )
        rows.append({
            "activity_id": activity.id, "name": activity.name,
            "zone": activity.zone, "planned": planned, "actual": actual,
            "variance": actual - planned if actual is not None and planned is not None else None,
        })
    return rows


def _activity_ids_for_zone(db: Session, project_id: int, zone: str | None) -> set[int] | None:
    if zone is None:
        return None
    return set(db.scalars(select(Activity.id).where(
        Activity.project_id == project_id, Activity.zone == zone
    )).all())


@router.get("/overview")
def overview(project_id: int, zone: str | None = None, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    project = db.get(Project, project_id)
    rows = _progress_rows(db, project_id, zone, None, None)
    activities = list(db.scalars(select(Activity).where(
        Activity.project_id == project_id, Activity.zone == zone if zone else True)).all())
    evidence = list(db.scalars(select(Evidence).where(Evidence.project_id == project_id)).all())
    today = date.today()
    attendance = list(db.scalars(select(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id, AttendanceRecord.attendance_date == today)).all())
    active_workers = set(db.scalars(select(WorkerAssignment.user_id).where(
        WorkerAssignment.project_id == project_id,
        WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE)).all())
    incidents = list(db.scalars(select(SafetyIncident).where(SafetyIncident.project_id == project_id)).all())
    defects = list(db.scalars(select(QualityDefect).where(QualityDefect.project_id == project_id)).all())
    materials = list(db.scalars(select(MaterialItem).where(MaterialItem.project_id == project_id)).all())
    disruptions = list(db.scalars(select(SiteDisruption).where(
        SiteDisruption.project_id == project_id, SiteDisruption.end_time.is_(None))).all())
    planned = [r["planned"] for r in rows if r["planned"] is not None]
    actual = [r["actual"] for r in rows if r["actual"] is not None]
    return {
        "project": {"id": project.id, "name": project.name, "status": project.status},
        "progress": {"overall_progress": sum(actual) / len(actual) if actual else 0,
                     "planned_progress": sum(planned) / len(planned) if planned else 0,
                     "variance": (sum(actual) / len(actual) - sum(planned) / len(planned)) if actual and planned else 0},
        "activities": {"total": len(activities), "completed": sum(a.status.value == "COMPLETED" for a in activities),
                       "in_progress": sum(a.status.value == "IN_PROGRESS" for a in activities),
                       "delayed": sum(a.status.value == "DELAYED" for a in activities)},
        "evidence": {"total": len(evidence), "verified": sum(e.status == EvidenceStatus.VERIFIED for e in evidence),
                     "pending": sum(e.status == EvidenceStatus.VERIFICATION_PENDING for e in evidence),
                     "rejected": sum(e.status == EvidenceStatus.REJECTED for e in evidence)},
        "workforce": {"total_workers": len(active_workers), "present_today": sum(a.status == AttendanceStatus.PRESENT for a in attendance)},
        "safety": {"open_incidents": sum(i.status != SafetyIncidentStatus.RESOLVED for i in incidents),
                   "critical_incidents": sum(i.severity == SafetyIncidentSeverity.CRITICAL for i in incidents)},
        "quality": {"open_defects": sum(d.status in {QualityDefectStatus.OPEN, QualityDefectStatus.IN_PROGRESS} for d in defects),
                    "critical_defects": sum(d.severity.value == "CRITICAL" and d.status != QualityDefectStatus.RESOLVED for d in defects)},
        "materials": {"low_stock_items": sum(m.current_quantity <= m.minimum_stock_level for m in materials)},
        "disruptions": {"active": len(disruptions)},
    }


@router.get("/progress")
def progress(project_id: int, zone: str | None = None, start_date: date | None = None,
             end_date: date | None = None, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    start, end = _range(start_date, end_date)
    rows = _progress_rows(db, project_id, zone, start, end)
    planned = [r["planned"] for r in rows if r["planned"] is not None]
    actual = [r["actual"] for r in rows if r["actual"] is not None]
    return {"overall": {"planned": sum(planned) / len(planned) if planned else 0,
                        "actual": sum(actual) / len(actual) if actual else 0,
                        "variance": (sum(actual) / len(actual) - sum(planned) / len(planned)) if actual and planned else 0},
            "activities": rows, "zones": _group_average(rows, "zone")}


def _group_average(rows: list[dict], key: str) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        if row.get(key):
            groups.setdefault(row[key], []).append(row)
    return [{"zone": name, "planned": _average([r["planned"] for r in values]),
             "actual": _average([r["actual"] for r in values])} for name, values in groups.items()]


def _average(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0


@router.get("/activities")
def activities(project_id: int, zone: str | None = None, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    items = list(db.scalars(select(Activity).where(
        Activity.project_id == project_id, Activity.zone == zone if zone else True)).all())
    rows = _progress_rows(db, project_id, zone, None, None)
    by_id = {r["activity_id"]: r for r in rows}
    risks = _latest_risk(list(db.scalars(select(ActivityRiskPrediction).where(
        ActivityRiskPrediction.project_id == project_id)).all()))
    return {"total": len(items), "completed": sum(a.status.value == "COMPLETED" for a in items),
            "in_progress": sum(a.status.value == "IN_PROGRESS" for a in items),
            "delayed": sum(a.status.value == "DELAYED" for a in items),
            "not_started": sum(a.status.value == "NOT_STARTED" for a in items),
            "critical_activities": [a.id for a in items if risks.get(a.id) and risks[a.id].risk_level == RiskLevel.CRITICAL],
            "activities": [{**by_id[a.id], "status": a.status, "risk_status": risks[a.id].risk_level if a.id in risks else None} for a in items]}


@router.get("/delays")
def delays(project_id: int, zone: str | None = None, db: Session = Depends(get_db),
           current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    ids = _activity_ids_for_zone(db, project_id, zone)
    query = select(ActivityRiskPrediction).where(
        ActivityRiskPrediction.project_id == project_id,
        ActivityRiskPrediction.predicted_delay_days > 0,
    )
    if ids is not None:
        query = query.where(ActivityRiskPrediction.activity_id.in_(ids))
    latest = _latest_risk(list(db.scalars(query).all()))
    activities = {a.id: a for a in db.scalars(select(Activity).where(Activity.project_id == project_id)).all()}
    return {"delayed_activities": [{"activity_id": a_id, "name": activities[a_id].name,
        "zone": activities[a_id].zone, "predicted_delay_days": item.predicted_delay_days,
        "risk_factors": item.risk_factors} for a_id, item in latest.items()]}


@router.get("/risks")
def risks(project_id: int, zone: str | None = None, db: Session = Depends(get_db),
          current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    ids = _activity_ids_for_zone(db, project_id, zone)
    query = select(ActivityRiskPrediction).where(
        ActivityRiskPrediction.project_id == project_id,
        ActivityRiskPrediction.prediction_status == RiskPredictionStatus.COMPLETED,
    )
    if ids is not None:
        query = query.where(ActivityRiskPrediction.activity_id.in_(ids))
    latest = _latest_risk(list(db.scalars(query).all()))
    rows = [{"activity_id": i, "risk_level": p.risk_level, "risk_score": p.risk_score,
             "primary_risk": p.primary_risk, "risk_factors": p.risk_factors} for i, p in latest.items()]
    return {"high_risk_activities": [r for r in rows if r["risk_level"] == RiskLevel.HIGH],
            "critical_risk_activities": [r for r in rows if r["risk_level"] == RiskLevel.CRITICAL],
            "risk_categories": dict(Counter(str(r["primary_risk"]) for r in rows)), "activities": rows}


@router.get("/workforce")
def workforce(project_id: int, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    workers = set(db.scalars(select(WorkerAssignment.user_id).where(
        WorkerAssignment.project_id == project_id,
        WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE)).all())
    today = list(db.scalars(select(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id, AttendanceRecord.attendance_date == date.today())).all())
    crews = len(db.scalars(select(Crew.id).where(
        Crew.project_id == project_id, Crew.is_active.is_(True)
    )).all())
    completed_hours = sum(
        (record.check_out - record.check_in).total_seconds() / 3600
        for record in today
        if record.check_in is not None and record.check_out is not None
    )
    activities = list(db.scalars(select(Activity).where(Activity.project_id == project_id)).all())
    required_workers = sum(activity.required_workers or 0 for activity in activities)
    shortage = 0
    for activity in activities:
        assigned_count = db.scalar(select(func.count(WorkerAssignment.id)).where(
            WorkerAssignment.activity_id == activity.id,
            WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE,
        )) or 0
        shortage += max((activity.required_workers or 0) - assigned_count, 0)
    return {"total_workers": len(workers), "present": sum(a.status == AttendanceStatus.PRESENT for a in today),
            "absent": sum(a.status == AttendanceStatus.ABSENT for a in today),
            "attendance_rate": sum(a.status == AttendanceStatus.PRESENT for a in today) / len(today) if today else 0,
            "active_crews": crews, "worker_hours_today": completed_hours,
            "worker_hours_records": sum(
                record.check_in is not None and record.check_out is not None for record in today
            ),
            "workforce_shortage": {
                "required_workers": required_workers or None,
                "available_workers": len(workers),
                "shortage_count": shortage if required_workers else None,
            },
            "activities_with_workforce_gaps": [], "workforce_gap_total": None}


@router.get("/materials")
def materials(project_id: int, start_date: date | None = None, end_date: date | None = None,
              db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    start_date, end_date = _range(start_date, end_date)
    items = list(db.scalars(select(MaterialItem).where(MaterialItem.project_id == project_id)).all())
    query = _date_filter(select(MaterialMovement).where(MaterialMovement.project_id == project_id),
                         MaterialMovement.movement_time, start_date, end_date)
    movements = list(db.scalars(query.order_by(MaterialMovement.movement_time.desc()).limit(50)).all())
    return {"total_material_types": len(items), "low_stock_materials": [m.name for m in items if m.current_quantity <= m.minimum_stock_level],
            "critical_stock_materials": [m.name for m in items if m.current_quantity <= 0],
            "recent_movements": [{"id": m.id, "material_id": m.material_id, "type": m.movement_type, "quantity": m.quantity, "movement_time": m.movement_time} for m in movements],
            "current_stock": [{"material_id": m.id, "name": m.name, "quantity": m.current_quantity, "minimum": m.minimum_stock_level} for m in items]}


@router.get("/equipment")
def equipment(project_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    equipment_items = list(db.scalars(select(Equipment).where(Equipment.project_id == project_id)).all())
    issues = len(db.scalars(select(EquipmentIssue.id).where(
        EquipmentIssue.project_id == project_id
    )).all())
    total = len(equipment_items)
    in_use = sum(e.status == EquipmentStatus.IN_USE for e in equipment_items)
    usage = list(db.scalars(select(EquipmentUsageRecord).where(
        EquipmentUsageRecord.project_id == project_id,
    )).all())
    observation_start = min((item.start_time for item in usage), default=None)
    observation_end = max((item.end_time for item in usage), default=None)
    observation_hours = (
        (observation_end - observation_start).total_seconds() / 3600 * total
        if observation_start and observation_end and total else 0
    )
    used_hours = sum((item.end_time - item.start_time).total_seconds() / 3600 for item in usage)
    return {"total_equipment": total,
            "available": sum(e.status == EquipmentStatus.AVAILABLE for e in equipment_items),
            "in_use": in_use,
            "maintenance": sum(e.status == EquipmentStatus.MAINTENANCE for e in equipment_items),
            "out_of_service": sum(e.status == EquipmentStatus.OUT_OF_SERVICE for e in equipment_items),
            "active_equipment_issues": issues,
            "utilization": {
                "value": in_use / total * 100 if total else None,
                "basis": "current_status",
                "historical": False,
            },
            "historical_utilization": {
                "value": used_hours / observation_hours * 100 if observation_hours else None,
                "usage_hours": used_hours,
                "observation_hours": observation_hours,
                "observation_start": observation_start,
                "observation_end": observation_end,
                "basis": "persisted_usage_records",
            }}


@router.get("/safety")
def safety(project_id: int, start_date: date | None = None, end_date: date | None = None,
           db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    start_date, end_date = _range(start_date, end_date)
    query = _date_filter(select(SafetyIncident).where(SafetyIncident.project_id == project_id),
                         SafetyIncident.occurred_at, start_date, end_date)
    items = list(db.scalars(query).all())
    ppe_query = select(PPEInspection).where(PPEInspection.project_id == project_id)
    if start_date:
        ppe_query = ppe_query.where(PPEInspection.inspection_date >= start_date)
    if end_date:
        ppe_query = ppe_query.where(PPEInspection.inspection_date <= end_date)
    ppe_items = list(db.scalars(ppe_query).all())
    ppe_compliant = sum(item.compliant for item in ppe_items)
    ppe_violations = len(ppe_items) - ppe_compliant
    return {"total_incidents": len(items), "open_incidents": sum(i.status != SafetyIncidentStatus.RESOLVED for i in items),
            "critical_incidents": sum(i.severity == SafetyIncidentSeverity.CRITICAL for i in items),
            "incidents_by_type": dict(Counter(i.incident_type.value for i in items)),
            "incidents_by_severity": dict(Counter(i.severity.value for i in items)),
            "ppe_compliance": {
                "percentage": ppe_compliant / len(ppe_items) * 100 if ppe_items else None,
                "compliant_count": ppe_compliant if ppe_items else None,
                "non_compliant_count": ppe_violations,
                "total_inspected": len(ppe_items),
            }}


@router.get("/quality")
def quality(project_id: int, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    inspections = list(db.scalars(select(QualityInspection).where(QualityInspection.project_id == project_id)).all())
    defects = list(db.scalars(select(QualityDefect).where(QualityDefect.project_id == project_id)).all())
    return {"inspections": len(inspections), "passed": sum(i.status == InspectionStatus.PASSED for i in inspections),
            "failed": sum(i.status == InspectionStatus.FAILED for i in inspections),
            "conditional": sum(i.status == InspectionStatus.CONDITIONAL for i in inspections),
            "open_defects": sum(d.status in {QualityDefectStatus.OPEN, QualityDefectStatus.IN_PROGRESS} for d in defects),
            "critical_defects": sum(d.severity.value == "CRITICAL" and d.status != QualityDefectStatus.RESOLVED for d in defects)}


@router.get("/disruptions")
def disruptions(project_id: int, zone: str | None = None, start_date: date | None = None,
                end_date: date | None = None, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    start_date, end_date = _range(start_date, end_date)
    query = select(SiteDisruption).where(SiteDisruption.project_id == project_id)
    if zone:
        query = query.where(SiteDisruption.zone == zone)
    query = _date_filter(query, SiteDisruption.start_time, start_date, end_date)
    items = list(db.scalars(query).all())
    weather_items = [i for i in items if i.type.value in {"WEATHER", "RAIN", "HEAT", "STORM", "HIGH_WIND", "FLOODING", "LIGHTNING", "VISIBILITY"}]
    return {"total_disruptions": len(items), "active_disruptions": sum(i.end_time is None for i in items),
            "total_interruption_minutes": sum(i.duration_minutes or 0 for i in items),
            "disruptions_by_type": dict(Counter(i.type.value for i in items)),
            "disruptions_by_severity": dict(Counter(i.severity.value for i in items)),
            "affected_zones": sorted({i.zone for i in items if i.zone}),
            "weather_impact": {
                "status": "IMPACTED" if weather_items else "NO_RECORDED_IMPACT",
                "disruptions": [{
                    "id": item.id,
                    "activity_id": item.activity_id,
                    "type": item.type,
                    "severity": item.severity,
                    "duration_minutes": item.duration_minutes,
                    "description": item.description,
                } for item in weather_items],
            }}


@router.get("/evidence")
def evidence(project_id: int, zone: str | None = None, start_date: date | None = None,
             end_date: date | None = None, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    start_date, end_date = _range(start_date, end_date)
    ids = _activity_ids_for_zone(db, project_id, zone)
    query = select(Evidence).where(Evidence.project_id == project_id)
    if ids is not None:
        query = query.where(Evidence.activity_id.in_(ids))
    query = _date_filter(query, Evidence.uploaded_at, start_date, end_date)
    items = list(db.scalars(query).all())
    activity_zones = dict(db.execute(select(Activity.id, Activity.zone).where(
        Activity.project_id == project_id
    )).all())
    comparisons = db.scalars(select(EvidenceComparisonAnalysis).where(
        EvidenceComparisonAnalysis.project_id == project_id).order_by(
        EvidenceComparisonAnalysis.created_at.desc()).limit(20)).all()
    return {"total_evidence": len(items), "verified": sum(e.status == EvidenceStatus.VERIFIED for e in items),
            "pending": sum(e.status == EvidenceStatus.VERIFICATION_PENDING for e in items),
            "rejected": sum(e.status == EvidenceStatus.REJECTED for e in items),
            "evidence_by_activity": dict(Counter(str(e.activity_id) for e in items)),
            "evidence_by_zone": dict(Counter(activity_zones.get(e.activity_id) for e in items if activity_zones.get(e.activity_id))),
            "recent_comparisons": [{"id": c.id, "activity_id": c.activity_id,
                "status": c.comparison_status, "created_at": c.created_at} for c in comparisons]}


@router.get("/productivity")
def productivity(project_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    rows = _progress_rows(db, project_id, None, None, None)
    planned = [float(row["planned"]) for row in rows if row["planned"] is not None]
    actual = [float(row["actual"]) for row in rows if row["actual"] is not None]
    if not planned or not actual:
        return {
            "value": None,
            "formula": "average_actual_progress / average_planned_progress * 100",
            "reason": "Both planned and actual progress are required.",
        }
    average_planned = sum(planned) / len(planned)
    average_actual = sum(actual) / len(actual)
    return {
        "value": average_actual / average_planned * 100 if average_planned else None,
        "average_planned_progress": average_planned,
        "average_actual_progress": average_actual,
        "formula": "average_actual_progress / average_planned_progress * 100",
        "activity_count": len(rows),
    }


@router.get("/schedule-approval")
def schedule_approval(project_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    schedule = db.scalar(select(ScheduleActivity).where(
        ScheduleActivity.project_id == project_id,
    ).order_by(ScheduleActivity.id.asc()))
    if schedule is None:
        return {"status": None, "approved_by": None, "approved_at": None}
    return {
        "status": schedule.schedule_approval_status,
        "approved_by": schedule.approved_by,
        "approved_at": schedule.approved_at,
    }


class ScheduleApprovalUpdate(BaseModel):
    status: ScheduleApprovalStatus


@router.patch("/schedule-approval")
def update_schedule_approval(project_id: int, data: ScheduleApprovalUpdate,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    if current_user.role not in PROJECT_WIDE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only project management roles may approve schedules")
    schedule = db.scalar(select(ScheduleActivity).where(
        ScheduleActivity.project_id == project_id,
    ).order_by(ScheduleActivity.id.asc()))
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    schedule.schedule_approval_status = data.status
    schedule.approved_by = current_user.id if data.status != ScheduleApprovalStatus.PENDING else None
    schedule.approved_at = datetime.now(timezone.utc) if data.status != ScheduleApprovalStatus.PENDING else None
    db.commit()
    db.refresh(schedule)
    return {
        "status": schedule.schedule_approval_status,
        "approved_by": schedule.approved_by,
        "approved_at": schedule.approved_at,
    }


@router.get("/replay")
def replay_aggregates(project_id: int, replay_date: date | None = None,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    _access(db, project_id, current_user)
    query = select(ConstructionEvent).where(ConstructionEvent.project_id == project_id)
    if replay_date is not None:
        start = datetime.combine(replay_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(replay_date, time.max, tzinfo=timezone.utc)
        query = query.where(
            ConstructionEvent.event_timestamp >= start,
            ConstructionEvent.event_timestamp <= end,
        )
    events = list(db.scalars(query.order_by(
        ConstructionEvent.event_timestamp.asc(), ConstructionEvent.id.asc()
    )).all())
    first = events[0].event_timestamp if events else None
    last = events[-1].event_timestamp if events else None
    return {
        "date": replay_date,
        "total_events": len(events),
        "first_event_time": first,
        "last_event_time": last,
        "event_types": dict(Counter(event.event_type.value for event in events)),
        "activity_event_counts": dict(Counter(
            str(event.activity_id) for event in events if event.activity_id is not None
        )),
        "evidence_events": sum(event.evidence_id is not None for event in events),
    }
