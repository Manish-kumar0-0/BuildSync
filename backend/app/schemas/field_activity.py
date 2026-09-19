from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.field_activity import AssignmentRole, AssignmentStatus, FieldActivityStatus


class ActivityCreate(BaseModel):
    schedule_activity_id: int = Field(gt=0)
    wbs_id: int | None = Field(default=None, gt=0)
    boq_item_id: int | None = Field(default=None, gt=0)
    activity_code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    zone: str | None = Field(default=None, max_length=100)


class ActivityUpdate(BaseModel):
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    zone: str | None = Field(default=None, max_length=100)


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    schedule_activity_id: int
    wbs_id: int | None
    boq_item_id: int | None
    activity_code: str
    name: str
    description: str | None
    location: str | None
    zone: str | None
    status: FieldActivityStatus
    progress_percentage: Decimal
    assigned_by: int | None
    responsible_user_id: int | None
    started_at: datetime | None
    completed_at: datetime | None
    last_updated_at: datetime
    created_at: datetime
    updated_at: datetime


class AssignmentCreate(BaseModel):
    user_id: int = Field(gt=0)
    assignment_role: AssignmentRole


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    user_id: int
    assigned_by: int | None
    assignment_role: AssignmentRole
    assigned_at: datetime
    status: AssignmentStatus


class ProgressUpdate(BaseModel):
    progress_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    notes: str | None = None


class ActivitySummary(BaseModel):
    project_id: int
    total_activities: int
    not_started: int
    started: int
    in_progress: int
    submitted: int
    verified: int
    completed: int
    delayed: int
    average_progress: Decimal
