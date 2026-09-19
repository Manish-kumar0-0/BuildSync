from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.workforce import AttendanceStatus, WorkforceAssignmentStatus


class CrewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    foreman_id: int | None = Field(default=None, gt=0)


class CrewResponse(CrewCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CrewMemberCreate(BaseModel):
    user_id: int = Field(gt=0)
    role: str | None = Field(default=None, max_length=50)


class CrewMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    crew_id: int
    user_id: int
    role: str | None
    is_active: bool
    joined_at: datetime


class WorkforceAssignmentCreate(BaseModel):
    activity_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    crew_id: int | None = Field(default=None, gt=0)
    role: str = Field(default="WORKER", min_length=1, max_length=50)


class WorkforceAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    activity_id: int
    user_id: int
    crew_id: int | None
    role: str
    status: WorkforceAssignmentStatus
    assigned_by: int | None
    assigned_at: datetime
    removed_at: datetime | None


class AttendanceCheckIn(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    check_in: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = None


class AttendanceCheckOut(BaseModel):
    check_out: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = None


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    user_id: int
    attendance_date: date
    status: AttendanceStatus
    check_in: datetime | None
    check_out: datetime | None
    check_in_latitude: float | None
    check_in_longitude: float | None
    check_out_latitude: float | None
    check_out_longitude: float | None
    notes: str | None


class AttendanceSummary(BaseModel):
    project_id: int
    start_date: date
    end_date: date
    total_records: int
    present: int
    checked_in: int
    checked_out: int
    unique_workers: int
