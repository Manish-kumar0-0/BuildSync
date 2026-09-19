from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity
from app.models.construction_event import ConstructionEventType
from app.models.workforce import (
    AttendanceRecord, AttendanceStatus, Crew, CrewMember, WorkerAssignment,
    WorkforceAssignmentStatus,
)
from app.schemas.workforce import (
    AttendanceCheckIn, AttendanceCheckOut, AttendanceResponse, AttendanceSummary,
    CrewCreate, CrewMemberCreate, CrewMemberResponse, CrewResponse,
    WorkforceAssignmentCreate, WorkforceAssignmentResponse,
)
from app.services.events.event_service import create_event

router = APIRouter(tags=["workforce"])
MANAGERS = {UserRole.PROJECT_MANAGER, UserRole.ADMIN, UserRole.SITE_ENGINEER}
FIELD_ROLES = {UserRole.WORKER, UserRole.FOREMAN, UserRole.FIELD_ENGINEER, UserRole.SITE_ENGINEER}


def project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


def manager(user: User) -> None:
    if user.role not in MANAGERS:
        raise HTTPException(403, "Workforce management access is required")


def user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(404, "Active user not found")
    if user.role not in FIELD_ROLES:
        raise HTTPException(422, "User role is not valid for workforce operations")
    return user


@router.post("/api/projects/{project_id}/crews", response_model=CrewResponse, status_code=201)
def create_crew(project_id: int, data: CrewCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    manager(current_user)
    project_or_404(db, project_id)
    if data.foreman_id:
        foreman = user_or_404(db, data.foreman_id)
        if foreman.role not in {UserRole.FOREMAN, UserRole.SITE_ENGINEER}:
            raise HTTPException(422, "Crew foreman must have a field leadership role")
    crew = Crew(project_id=project_id, **data.model_dump())
    db.add(crew)
    db.commit()
    db.refresh(crew)
    return crew


@router.get("/api/projects/{project_id}/crews", response_model=list[CrewResponse])
def list_crews(project_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    return list(db.scalars(select(Crew).where(Crew.project_id == project_id).order_by(Crew.id)).all())


@router.post("/api/crews/{crew_id}/members", response_model=CrewMemberResponse, status_code=201)
def add_crew_member(crew_id: int, data: CrewMemberCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    manager(current_user)
    crew = db.get(Crew, crew_id)
    if crew is None:
        raise HTTPException(404, "Crew not found")
    user_or_404(db, data.user_id)
    member = db.scalar(select(CrewMember).where(CrewMember.crew_id == crew_id, CrewMember.user_id == data.user_id))
    if member:
        member.is_active = True
        member.role = data.role
    else:
        member = CrewMember(crew_id=crew_id, **data.model_dump())
        db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/api/crews/{crew_id}/members", response_model=list[CrewMemberResponse])
def list_crew_members(crew_id: int, db: Session = Depends(get_db),
                       _: User = Depends(get_current_user)):
    if db.get(Crew, crew_id) is None:
        raise HTTPException(404, "Crew not found")
    return list(db.scalars(select(CrewMember).where(CrewMember.crew_id == crew_id, CrewMember.is_active.is_(True))).all())


@router.post("/api/projects/{project_id}/workforce/assignments",
             response_model=WorkforceAssignmentResponse, status_code=201)
def assign_worker(project_id: int, data: WorkforceAssignmentCreate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    manager(current_user)
    project_or_404(db, project_id)
    activity = db.get(Activity, data.activity_id)
    if activity is None or activity.project_id != project_id:
        raise HTTPException(422, "Activity must belong to the project")
    user_or_404(db, data.user_id)
    if data.crew_id:
        crew = db.get(Crew, data.crew_id)
        if crew is None or crew.project_id != project_id:
            raise HTTPException(422, "Crew must belong to the project")
    assignment = db.scalar(select(WorkerAssignment).where(
        WorkerAssignment.activity_id == data.activity_id, WorkerAssignment.user_id == data.user_id))
    if assignment:
        assignment.status = WorkforceAssignmentStatus.ACTIVE
        assignment.crew_id = data.crew_id
        assignment.role = data.role
        assignment.assigned_by = current_user.id
        assignment.removed_at = None
    else:
        assignment = WorkerAssignment(project_id=project_id, assigned_by=current_user.id, **data.model_dump())
        db.add(assignment)
    db.flush()
    create_event(db, project_id=project_id, activity_id=activity.id, wbs_id=activity.wbs_id,
                 event_type=ConstructionEventType.WORKFORCE_ASSIGNED, actor_user_id=current_user.id,
                 title="Worker assigned", description=f"Worker {data.user_id} assigned to {activity.name}.",
                 metadata={"user_id": data.user_id, "crew_id": data.crew_id, "role": data.role},
                 reference_type="worker_assignment", reference_id=assignment.id)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/api/projects/{project_id}/workforce/assignments",
            response_model=list[WorkforceAssignmentResponse])
def list_worker_assignments(project_id: int, activity_id: int | None = Query(None, gt=0),
                             db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    query = select(WorkerAssignment).where(WorkerAssignment.project_id == project_id)
    if activity_id:
        query = query.where(WorkerAssignment.activity_id == activity_id)
    return list(db.scalars(query.order_by(WorkerAssignment.id)).all())


@router.delete("/api/projects/{project_id}/workforce/assignments/{assignment_id}", status_code=204)
def remove_worker_assignment(project_id: int, assignment_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    manager(current_user)
    assignment = db.scalar(select(WorkerAssignment).where(
        WorkerAssignment.id == assignment_id, WorkerAssignment.project_id == project_id))
    if assignment is None:
        raise HTTPException(404, "Worker assignment not found")
    assignment.status = WorkforceAssignmentStatus.REMOVED
    assignment.removed_at = datetime.now(timezone.utc)
    create_event(db, project_id=project_id, activity_id=assignment.activity_id,
                 event_type=ConstructionEventType.WORKFORCE_UNASSIGNED, actor_user_id=current_user.id,
                 title="Worker unassigned", description=f"Worker {assignment.user_id} unassigned.",
                 metadata={"user_id": assignment.user_id}, reference_type="worker_assignment",
                 reference_id=assignment.id)
    db.commit()


def _attendance_user(data_user_id: int | None, current_user: User) -> int:
    if data_user_id and current_user.role in MANAGERS:
        return data_user_id
    if data_user_id and data_user_id != current_user.id:
        raise HTTPException(403, "You may only record your own attendance")
    return current_user.id


@router.post("/api/projects/{project_id}/attendance/check-in", response_model=AttendanceResponse)
def check_in(project_id: int, data: AttendanceCheckIn, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    user_id = _attendance_user(data.user_id, current_user)
    user_or_404(db, user_id)
    now = data.check_in or datetime.now(timezone.utc)
    record = db.scalar(select(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id, AttendanceRecord.user_id == user_id,
        AttendanceRecord.attendance_date == now.date()))
    if record and record.check_in:
        raise HTTPException(409, "Attendance already checked in")
    if record is None:
        record = AttendanceRecord(project_id=project_id, user_id=user_id, attendance_date=now.date())
        db.add(record)
    record.status = AttendanceStatus.PRESENT
    record.check_in = now
    record.check_in_latitude = data.latitude
    record.check_in_longitude = data.longitude
    record.notes = data.notes
    db.flush()
    create_event(db, project_id=project_id, actor_user_id=current_user.id,
                 event_type=ConstructionEventType.ATTENDANCE_CHECK_IN, title="Worker checked in",
                 description=f"Worker {user_id} checked in.", metadata={"user_id": user_id},
                 reference_type="attendance", reference_id=record.id)
    db.commit()
    db.refresh(record)
    return record


@router.post("/api/projects/{project_id}/attendance/check-out", response_model=AttendanceResponse)
def check_out(project_id: int, data: AttendanceCheckOut, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    now = data.check_out or datetime.now(timezone.utc)
    record = db.scalar(select(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id, AttendanceRecord.user_id == current_user.id,
        AttendanceRecord.attendance_date == now.date()))
    if record is None or record.check_in is None:
        raise HTTPException(409, "Attendance check-in is required")
    if record.check_out:
        raise HTTPException(409, "Attendance already checked out")
    record.check_out = now
    record.check_out_latitude = data.latitude
    record.check_out_longitude = data.longitude
    if data.notes:
        record.notes = data.notes
    db.flush()
    create_event(db, project_id=project_id, actor_user_id=current_user.id,
                 event_type=ConstructionEventType.ATTENDANCE_CHECK_OUT, title="Worker checked out",
                 description=f"Worker {current_user.id} checked out.", metadata={"user_id": current_user.id},
                 reference_type="attendance", reference_id=record.id)
    db.commit()
    db.refresh(record)
    return record


@router.get("/api/projects/{project_id}/attendance/daily", response_model=list[AttendanceResponse])
def daily_attendance(project_id: int, attendance_date: date | None = Query(None, alias="date"),
                     db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    target = attendance_date or date.today()
    return list(db.scalars(select(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id, AttendanceRecord.attendance_date == target
    ).order_by(AttendanceRecord.user_id)).all())


@router.get("/api/projects/{project_id}/attendance/summary", response_model=AttendanceSummary)
def attendance_summary(project_id: int, start_date: date | None = None, end_date: date | None = None,
                       db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    start = start_date or date.today()
    end = end_date or start
    if start > end:
        raise HTTPException(422, "start_date must not exceed end_date")
    records = list(db.scalars(select(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id,
        AttendanceRecord.attendance_date >= start, AttendanceRecord.attendance_date <= end
    )).all())
    return AttendanceSummary(project_id=project_id, start_date=start, end_date=end,
                             total_records=len(records), present=sum(r.status == AttendanceStatus.PRESENT for r in records),
                             checked_in=sum(r.check_in is not None for r in records),
                             checked_out=sum(r.check_out is not None for r in records),
                             unique_workers=len({r.user_id for r in records}))


@router.get("/api/projects/{project_id}/workforce/summary")
def workforce_summary(project_id: int, attendance_date: date | None = Query(None, alias="date"),
                      db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    project_or_404(db, project_id)
    target = attendance_date or date.today()
    active_assignments = db.scalar(select(func.count()).select_from(WorkerAssignment).where(
        WorkerAssignment.project_id == project_id,
        WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE
    )) or 0
    assigned_workers = db.scalar(select(func.count(func.distinct(WorkerAssignment.user_id))).where(
        WorkerAssignment.project_id == project_id,
        WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE
    )) or 0
    present = db.scalar(select(func.count()).select_from(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id,
        AttendanceRecord.attendance_date == target,
        AttendanceRecord.status == AttendanceStatus.PRESENT
    )) or 0
    checked_out = db.scalar(select(func.count()).select_from(AttendanceRecord).where(
        AttendanceRecord.project_id == project_id,
        AttendanceRecord.attendance_date == target,
        AttendanceRecord.check_out.is_not(None)
    )) or 0
    return {
        "project_id": project_id, "date": target,
        "active_assignments": active_assignments,
        "assigned_workers": assigned_workers,
        "present_workers": present,
        "checked_out_workers": checked_out,
    }


@router.get("/api/activities/{activity_id}/workforce",
            response_model=list[WorkforceAssignmentResponse])
def activity_workforce(activity_id: int, db: Session = Depends(get_db),
                       _: User = Depends(get_current_user)):
    if db.get(Activity, activity_id) is None:
        raise HTTPException(404, "Field activity not found")
    return list(db.scalars(select(WorkerAssignment).where(
        WorkerAssignment.activity_id == activity_id,
        WorkerAssignment.status == WorkforceAssignmentStatus.ACTIVE
    ).order_by(WorkerAssignment.id)).all())
