"""Create the repeatable BuildSync SIH demonstration dataset.

This module only touches the project identified by ``ML6-C3`` and users whose
email ends in ``@buildsync.demo``.
"""

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.database import Base, SessionLocal, engine
from app.core.database import ensure_schema
from app.core.security import hash_password
from app.models import (
    Activity,
    ActivityAssignment,
    ActivityRiskPrediction,
    ActivityStatus,
    AssignmentRole,
    AssignmentStatus,
    AttendanceRecord,
    AttendanceStatus,
    BOQItem,
    ConstructionEvent,
    ConstructionEventType,
    Crew,
    CrewMember,
    Equipment,
    EquipmentIssue,
    EquipmentIssueSeverity,
    EquipmentUsageRecord,
    EquipmentStatus,
    Evidence,
    EvidenceStatus,
    EvidenceType,
    FieldActivityStatus,
    InspectionStatus,
    InspectionType,
    MaterialItem,
    NotificationPriority,
    NotificationType,
    PlannedProgress,
    PrimaryRisk,
    Project,
    ProjectConfiguration,
    ProjectMemory,
    ProjectStatus,
    ProjectUserAssignment,
    ProjectAssignmentStatus,
    ProjectZone,
    PPEInspection,
    QualityDefect,
    QualityDefectStatus,
    QualityInspection,
    QualitySeverity,
    RecoveryRecommendation,
    RecommendationImpact,
    RecommendationPriority,
    RecommendationStatus,
    RecommendationType,
    ImplementationEffort,
    RiskLevel,
    RiskPredictionStatus,
    SafetyIncident,
    SafetyIncidentSeverity,
    SafetyIncidentStatus,
    SafetyIncidentType,
    ScheduleActivity,
    ScheduleApprovalStatus,
    SiteDisruption,
    SiteDisruptionSeverity,
    SiteDisruptionSource,
    SiteDisruptionType,
    User,
    UserRole,
    WBS,
    WBSStatus,
    WorkforceAssignment,
    WorkforceAssignmentStatus,
)
from app.services.events.event_service import create_event
from app.services.notifications.notification_service import create_notification

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD")
PROJECT_CODE = "ML6-C3"
DEMO_DOMAIN = "@buildsync.demo"
DEMO_DATE = date(2026, 9, 16)
DEMO_ZONE_NAMES = ("North Viaduct", "Pier P3", "Pier P4", "Pier P5", "Casting Yard")
ROLE_USERS = {
    "admin": ("Demo Admin", UserRole.ADMIN),
    "pm": ("Demo Project Manager", UserRole.PROJECT_MANAGER),
    "engineer": ("Demo Field Engineer", UserRole.FIELD_ENGINEER),
}


def _user(db, key: str, name: str, role: UserRole) -> User:
    email = f"{key}{DEMO_DOMAIN}"
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            full_name=name,
            email=email,
            hashed_password=hash_password(DEMO_PASSWORD),
            role=role,
        )
        db.add(user)
        db.flush()
    else:
        user.hashed_password = hash_password(DEMO_PASSWORD)
    return user


def _event(db, project, activity, event_type, when, title, actor, reference, metadata=None):
    return create_event(
        db,
        project_id=project.id,
        activity_id=activity.id if activity else None,
        wbs_id=activity.wbs_id if activity else None,
        event_type=event_type,
        event_timestamp=when,
        title=title,
        description=f"Demo record: {title}.",
        actor_user_id=actor.id if actor else None,
        zone=activity.zone if activity else "Pier P3",
        metadata=metadata,
        reference_type="demo-seed",
        reference_id=reference,
    )


def seed_demo() -> None:
    if not DEMO_PASSWORD:
        raise RuntimeError("DEMO_PASSWORD must be configured before seeding demo data")
    if engine is None or SessionLocal is None:
        raise RuntimeError("DATABASE_URL must be configured before seeding demo data")
    ensure_schema()
    with SessionLocal() as db:
        if not DEMO_PASSWORD:
            raise RuntimeError("DEMO_PASSWORD must be configured before seeding demo data")
        users = {key: _user(db, key, name, role) for key, (name, role) in ROLE_USERS.items()}
        workers = [users["engineer"]]
        for index in range(1, 20):
            workers.append(_user(db, f"worker{index:02d}", f"Demo Worker {index:02d}", UserRole.WORKER))

        project = db.scalar(select(Project).where(Project.project_code == PROJECT_CODE))
        if project is None:
            project = Project(
                project_code=PROJECT_CODE,
                name="Metro Line 6 — Package C3",
                description="Safe SIH demonstration project dataset.",
                location="North Viaduct",
                package_name="Package C3",
                start_date=date(2026, 1, 1),
                planned_end_date=date(2027, 12, 31),
                status=ProjectStatus.ACTIVE,
                created_by=users["pm"].id,
            )
            db.add(project)
            db.flush()

        for name in DEMO_ZONE_NAMES:
            if db.scalar(select(ProjectZone).where(ProjectZone.project_id == project.id, ProjectZone.name == name)) is None:
                db.add(ProjectZone(project_id=project.id, name=name, description=f"Demo zone: {name}"))
        if db.scalar(select(ProjectConfiguration).where(ProjectConfiguration.project_id == project.id)) is None:
            db.add(ProjectConfiguration(project_id=project.id, timezone="Asia/Kolkata", default_zone="Pier P3"))

        for user in users.values():
            if db.scalar(select(ProjectUserAssignment).where(
                ProjectUserAssignment.project_id == project.id,
                ProjectUserAssignment.user_id == user.id,
                ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE,
            )) is None:
                db.add(ProjectUserAssignment(
                    project_id=project.id, user_id=user.id, role=user.role,
                    status=ProjectAssignmentStatus.ACTIVE,
                ))

        wbs_by_name = {}
        for code, name in (("03", "Pier Works"), ("03.01", "Pier P3"), ("04", "Pier P4"), ("05", "Casting and Launch")):
            wbs = db.scalar(select(WBS).where(WBS.project_id == project.id, WBS.wbs_code == code))
            if wbs is None:
                wbs = WBS(project_id=project.id, wbs_code=code, name=name, level=code.count(".") + 1, status=WBSStatus.IN_PROGRESS)
                db.add(wbs)
                db.flush()
            wbs_by_name[name] = wbs

        activity_specs = [
            ("P3-REBAR", "Pier P3 Reinforcement", "Pier P3", 68, 63, wbs_by_name["Pier P3"]),
            ("P3-FORM", "Pier P3 Formwork", "Pier P3", 45, 42, wbs_by_name["Pier P3"]),
            ("P3-CONC", "Pier P3 Concrete Pour", "Pier P3", 25, 20, wbs_by_name["Pier P3"]),
            ("P4-REBAR", "Pier P4 Reinforcement", "Pier P4", 38, 38, wbs_by_name["Pier P4"]),
            ("P4-FORM", "Pier P4 Formwork", "Pier P4", 30, 28, wbs_by_name["Pier P4"]),
            ("CAST-01", "Segment Casting", "Casting Yard", 52, 50, wbs_by_name["Casting and Launch"]),
            ("GL-01", "Girder Launch Preparation", "North Viaduct", 18, 18, wbs_by_name["Casting and Launch"]),
        ]
        activities = {}
        for code, name, zone, planned, reported, wbs in activity_specs:
            schedule = db.scalar(select(ScheduleActivity).where(ScheduleActivity.project_id == project.id, ScheduleActivity.activity_code == code))
            if schedule is None:
                schedule = ScheduleActivity(
                    project_id=project.id, wbs_id=wbs.id, activity_code=code, name=name,
                    description=f"Demo schedule activity: {name}.",
                    planned_start=date(2026, 8, 1), planned_finish=date(2026, 10, 15),
                    planned_quantity=Decimal("100"), planned_progress=Decimal(str(planned)),
                    weightage=Decimal("14.28"), status=ActivityStatus.DELAYED if code == "P3-REBAR" else ActivityStatus.IN_PROGRESS,
                )
                db.add(schedule)
                db.flush()
            activity = db.scalar(select(Activity).where(Activity.schedule_activity_id == schedule.id))
            if activity is None:
                activity = Activity(
                    project_id=project.id, schedule_activity_id=schedule.id, wbs_id=wbs.id,
                    activity_code=code, name=name, zone=zone, location=zone,
                    assigned_by=users["pm"].id, responsible_user_id=users["engineer"].id,
                    status=FieldActivityStatus.IN_PROGRESS,
                    progress_percentage=Decimal(str(reported)),
                )
                db.add(activity)
                db.flush()
            if code == "P3-REBAR" and activity.required_workers is None:
                activity.required_workers = 20
            activities[code] = activity
            if db.scalar(select(PlannedProgress).where(PlannedProgress.schedule_activity_id == schedule.id, PlannedProgress.date == DEMO_DATE)) is None:
                db.add(PlannedProgress(
                    schedule_activity_id=schedule.id,
                    date=DEMO_DATE,
                    planned_percentage=Decimal(str(planned)),
                    planned_quantity=Decimal(str(planned)),
                ))

        p3 = activities["P3-REBAR"]
        p3_schedule = db.get(ScheduleActivity, p3.schedule_activity_id)
        if p3_schedule and p3_schedule.schedule_approval_status == ScheduleApprovalStatus.PENDING:
            p3_schedule.schedule_approval_status = ScheduleApprovalStatus.APPROVED
            p3_schedule.approved_by = users["pm"].id
            p3_schedule.approved_at = datetime(2026, 9, 15, 9, tzinfo=timezone.utc)
        if db.scalar(select(Evidence).where(Evidence.project_id == project.id, Evidence.activity_id == p3.id, Evidence.file_name == "demo-pier-p3-evidence.jpg")) is None:
            db.add(Evidence(
                project_id=project.id, activity_id=p3.id, uploaded_by=users["engineer"].id,
                evidence_type=EvidenceType.PHOTO, file_name="demo-pier-p3-evidence.jpg",
                file_path="uploads/1/1/2026-09-15/a92afc2291104bd2b6a493d95db1685c.jpg",
                file_size=0, mime_type="image/jpeg", latitude=Decimal("19.076"), longitude=Decimal("72.877"),
                gps_accuracy=Decimal("2"), captured_at=datetime(2026, 9, 16, 11, 30, tzinfo=timezone.utc),
                reported_progress=Decimal("63"), notes="Demo evidence for manual AI-analysis testing.",
                status=EvidenceStatus.VERIFICATION_PENDING,
            ))
            db.flush()

        if db.scalar(select(SiteDisruption).where(SiteDisruption.project_id == project.id, SiteDisruption.description == "Demo heavy rainfall at Pier P3")) is None:
            db.add(SiteDisruption(
                project_id=project.id, activity_id=p3.id, type=SiteDisruptionType.RAIN,
                severity=SiteDisruptionSeverity.HIGH, start_time=datetime(2026, 9, 16, 14, tzinfo=timezone.utc),
                end_time=datetime(2026, 9, 16, 15, 30, tzinfo=timezone.utc), duration_minutes=90,
                zone="Pier P3", description="Demo heavy rainfall at Pier P3",
                source=SiteDisruptionSource.MANUAL, created_by=users["engineer"].id,
            ))

        crew = db.scalar(select(Crew).where(Crew.project_id == project.id, Crew.name == "Demo Civil Crew A"))
        if crew is None:
            crew = Crew(project_id=project.id, name="Demo Civil Crew A", description="18 assigned, 15 present", foreman_id=users["engineer"].id)
            db.add(crew)
            db.flush()
        for worker in workers[:18]:
            if db.scalar(select(CrewMember).where(CrewMember.crew_id == crew.id, CrewMember.user_id == worker.id)) is None:
                db.add(CrewMember(crew_id=crew.id, user_id=worker.id, role="WORKER"))
            if db.scalar(select(WorkforceAssignment).where(WorkforceAssignment.activity_id == p3.id, WorkforceAssignment.user_id == worker.id)) is None:
                db.add(WorkforceAssignment(project_id=project.id, activity_id=p3.id, user_id=worker.id, crew_id=crew.id, role="FIELD_ENGINEER", assigned_by=users["engineer"].id, status=WorkforceAssignmentStatus.ACTIVE))
            if db.scalar(select(AttendanceRecord).where(AttendanceRecord.project_id == project.id, AttendanceRecord.user_id == worker.id, AttendanceRecord.attendance_date == DEMO_DATE)) is None:
                db.add(AttendanceRecord(project_id=project.id, user_id=worker.id, attendance_date=DEMO_DATE, status=AttendanceStatus.PRESENT if worker in workers[:15] else AttendanceStatus.ABSENT, check_in=datetime(2026, 9, 16, 7, 30, tzinfo=timezone.utc) if worker in workers[:15] else None, check_out=datetime(2026, 9, 16, 16, tzinfo=timezone.utc) if worker in workers[:15] else None))
            elif worker in workers[:15]:
                attendance = db.scalar(select(AttendanceRecord).where(AttendanceRecord.project_id == project.id, AttendanceRecord.user_id == worker.id, AttendanceRecord.attendance_date == DEMO_DATE))
                if attendance.check_in is not None and attendance.check_out is None:
                    attendance.check_out = datetime(2026, 9, 16, 16, tzinfo=timezone.utc)

        today = date.today()
        for worker in workers[:15]:
            if db.scalar(select(AttendanceRecord).where(
                AttendanceRecord.project_id == project.id,
                AttendanceRecord.user_id == worker.id,
                AttendanceRecord.attendance_date == today,
            )) is None:
                db.add(AttendanceRecord(
                    project_id=project.id, user_id=worker.id, attendance_date=today,
                    status=AttendanceStatus.PRESENT,
                    check_in=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=7, minute=30),
                    check_out=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=16),
                    notes="Development demo attendance record.",
                ))

        for index, worker in enumerate(workers[:18]):
            if db.scalar(select(PPEInspection).where(
                PPEInspection.project_id == project.id,
                PPEInspection.worker_id == worker.id,
                PPEInspection.inspection_date == DEMO_DATE,
            )) is None:
                db.add(PPEInspection(
                    project_id=project.id, worker_id=worker.id, inspection_date=DEMO_DATE,
                    compliant=index < 15, violation_type=None if index < 15 else "MISSING_HELMET",
                    inspected_by=users["engineer"].id,
                ))

        for name, unit, current, minimum in (("Reinforcement Steel", "ton", 18, 40), ("Concrete", "m3", 120, 50), ("Formwork Material", "m2", 240, 80)):
            if db.scalar(select(MaterialItem).where(MaterialItem.project_id == project.id, MaterialItem.name == name)) is None:
                db.add(MaterialItem(project_id=project.id, name=name, material_code=f"DEMO-{name[:3].upper()}", unit=unit, planned_quantity=Decimal("500"), current_quantity=Decimal(str(current)), minimum_stock_level=Decimal(str(minimum))))

        equipment_specs = (("Tower Crane", "TC-01", EquipmentStatus.AVAILABLE), ("Concrete Pump", "CP-01", EquipmentStatus.IN_USE), ("Excavator", "EX-01", EquipmentStatus.MAINTENANCE))
        for name, code, status in equipment_specs:
            item = db.scalar(select(Equipment).where(Equipment.project_id == project.id, Equipment.equipment_code == code))
            if item is None:
                item = Equipment(project_id=project.id, name=name, equipment_code=code, equipment_type=name, status=status, zone="Pier P3")
                db.add(item)
                db.flush()
            if code == "EX-01" and db.scalar(select(EquipmentIssue).where(EquipmentIssue.equipment_id == item.id)) is None:
                db.add(EquipmentIssue(
                    equipment_id=item.id,
                    project_id=project.id,
                    activity_id=p3.id,
                    issue_type="MAINTENANCE",
                    severity=EquipmentIssueSeverity.HIGH,
                    description="Excavator is unavailable for scheduled support.",
                    reported_at=datetime(2026, 9, 16, 15, tzinfo=timezone.utc),
                    reported_by=users["engineer"].id,
                ))
            if db.scalar(select(EquipmentUsageRecord).where(
                EquipmentUsageRecord.equipment_id == item.id,
                EquipmentUsageRecord.start_time == datetime(2026, 9, 16, 7, tzinfo=timezone.utc),
            )) is None:
                hours = {"TC-01": 6, "CP-01": 8, "EX-01": 4}[code]
                db.add(EquipmentUsageRecord(
                    project_id=project.id, equipment_id=item.id, activity_id=p3.id,
                    start_time=datetime(2026, 9, 16, 7, tzinfo=timezone.utc),
                    end_time=datetime(2026, 9, 16, 7 + hours, tzinfo=timezone.utc),
                    recorded_by=users["engineer"].id,
                    notes="Development demo usage record for historical utilization validation.",
                ))

        for incident_type, severity, description, hour in ((SafetyIncidentType.NEAR_MISS, SafetyIncidentSeverity.MEDIUM, "Demo near miss: unsecured tool near Pier P3.", 17), (SafetyIncidentType.INCIDENT, SafetyIncidentSeverity.HIGH, "Demo high safety incident: exclusion-zone breach.", 17)):
            if db.scalar(select(SafetyIncident).where(SafetyIncident.project_id == project.id, SafetyIncident.description == description)) is None:
                db.add(SafetyIncident(project_id=project.id, activity_id=p3.id, reported_by=users["engineer"].id, incident_type=incident_type, severity=severity, description=description, zone="Pier P3", occurred_at=datetime(2026, 9, 16, hour, tzinfo=timezone.utc), status=SafetyIncidentStatus.OPEN))

        failed_inspection = None
        for index, status in enumerate((InspectionStatus.PASSED, InspectionStatus.PASSED, InspectionStatus.PASSED, InspectionStatus.FAILED)):
            inspection = db.scalar(select(QualityInspection).where(QualityInspection.project_id == project.id, QualityInspection.notes == f"Demo inspection {index + 1}"))
            if inspection is None:
                inspection = QualityInspection(project_id=project.id, activity_id=p3.id, inspector_id=users["engineer"].id, inspection_type=InspectionType.WORKMANSHIP, status=status, score=92 if status == InspectionStatus.PASSED else 58, notes=f"Demo inspection {index + 1}", inspected_at=datetime(2026, 9, 16, 16, tzinfo=timezone.utc))
                db.add(inspection)
                db.flush()
            if status == InspectionStatus.FAILED:
                failed_inspection = inspection
        if failed_inspection and db.scalar(select(QualityDefect).where(QualityDefect.inspection_id == failed_inspection.id)) is None:
            db.add(QualityDefect(project_id=project.id, activity_id=p3.id, inspection_id=failed_inspection.id, severity=QualitySeverity.HIGH, description="Demo reinforcement cover below tolerance.", location="Pier P3 west face", status=QualityDefectStatus.OPEN, reported_by=users["engineer"].id))

        db.flush()
        risk = db.scalar(select(ActivityRiskPrediction).where(ActivityRiskPrediction.activity_id == p3.id, ActivityRiskPrediction.model_version == "demo-1"))
        if risk is None:
            risk = ActivityRiskPrediction(project_id=project.id, activity_id=p3.id, schedule_activity_id=p3.schedule_activity_id, prediction_date=DEMO_DATE, risk_level=RiskLevel.HIGH, risk_score=Decimal("72"), predicted_delay_days=Decimal("2"), confidence_score=Decimal("88"), primary_risk=PrimaryRisk.RESOURCE_CONSTRAINT, risk_factors=[{"factor": "low_stock", "severity": "HIGH"}, {"factor": "weather", "severity": "HIGH"}], explanation="Demo risk record derived from the seeded low stock, workforce gap, and weather disruption.", model_name="existing-risk-service", model_version="demo-1", prediction_status=RiskPredictionStatus.COMPLETED)
            db.add(risk)
            db.flush()
        if db.scalar(select(RecoveryRecommendation).where(RecoveryRecommendation.risk_prediction_id == risk.id)) is None:
            db.add(RecoveryRecommendation(project_id=project.id, activity_id=p3.id, risk_prediction_id=risk.id, recommendation_type=RecommendationType.ADD_WORKFORCE, priority=RecommendationPriority.HIGH, title="Add workforce to Pier P3 reinforcement", description="Demo recommendation: assign five additional workers after material availability is confirmed.", expected_impact=RecommendationImpact.HIGH, implementation_effort=ImplementationEffort.MEDIUM, status=RecommendationStatus.SUGGESTED))

        event_specs = (
            (7, 30, ConstructionEventType.ATTENDANCE_CHECK_IN, "Workers checked in"),
            (8, 0, ConstructionEventType.WORK_START, "Pier P3 reinforcement work started"),
            (10, 15, ConstructionEventType.MATERIAL_RECEIVED, "Material delivery recorded"),
            (11, 30, ConstructionEventType.EVIDENCE_CAPTURED, "Evidence uploaded"),
            (13, 0, ConstructionEventType.PROGRESS_REPORTED, "Progress updated"),
            (14, 0, ConstructionEventType.WEATHER_INTERRUPTION, "Weather interruption"),
            (15, 30, ConstructionEventType.WORK_RESUMED, "Work resumed"),
            (16, 0, ConstructionEventType.QUALITY_INSPECTION_FAILED, "Quality inspection failed"),
            (17, 0, ConstructionEventType.SAFETY_INCIDENT, "Safety issue reported"),
            (18, 0, ConstructionEventType.PROGRESS_REPORTED, "Day-end progress recorded"),
        )
        for index, (hour, minute, event_type, title) in enumerate(event_specs, 1):
            _event(db, project, p3, event_type, datetime(2026, 9, 16, hour, minute, tzinfo=timezone.utc), title, users["pm"], index, {"severity": "HIGH"} if event_type in {ConstructionEventType.WEATHER_INTERRUPTION, ConstructionEventType.SAFETY_INCIDENT} else {"progress_percentage": 63} if event_type == ConstructionEventType.PROGRESS_REPORTED else None)
        db.flush()
        for notification_type, priority, title, message, reference in (
            (NotificationType.HIGH_RISK, NotificationPriority.HIGH, "Pier P3 high risk", "Demo risk: Pier P3 is behind plan.", risk.id),
            (NotificationType.MATERIAL, NotificationPriority.HIGH, "Reinforcement steel low stock", "Demo material stock is below the minimum level.", p3.id),
            (NotificationType.WORKFORCE, NotificationPriority.HIGH, "Workforce gap", "Demo crew has 15 present against 20 planned.", crew.id),
            (NotificationType.SAFETY, NotificationPriority.HIGH, "High safety issue", "Demo high-severity safety incident requires review.", p3.id),
            (NotificationType.QUALITY, NotificationPriority.HIGH, "Quality inspection failed", "Demo failed inspection has an open high defect.", failed_inspection.id if failed_inspection else p3.id),
        ):
            create_notification(db, recipient_user_id=users["pm"].id, project_id=project.id, activity_id=p3.id, notification_type=notification_type, priority=priority, title=title, message=message, reference_type="demo-seed", reference_id=reference)
        db.commit()
        print(f"Demo project ensured: {PROJECT_CODE} (id={project.id})")


if __name__ == "__main__":
    seed_demo()
