from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.planning import ProjectStatus
from app.models.project_admin import ProjectAssignmentStatus
from app.models.user import UserRole


class AdminProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    project_code: str = Field(min_length=1, max_length=50)
    description: str | None = None
    location: str | None = None
    start_date: date
    planned_end_date: date

    @model_validator(mode="after")
    def valid_dates(self):
        if self.planned_end_date < self.start_date:
            raise ValueError("planned_end_date cannot be before start_date")
        return self


class AdminProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    project_code: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    location: str | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    actual_end_date: date | None = None
    status: ProjectStatus | None = None


class AdminProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    project_code: str
    description: str | None
    location: str | None
    status: ProjectStatus
    start_date: date
    planned_end_date: date
    actual_end_date: date | None
    created_at: datetime
    updated_at: datetime


class ProjectUserAssignmentCreate(BaseModel):
    user_id: int = Field(gt=0)
    role: UserRole


class ProjectUserAssignmentUpdate(BaseModel):
    role: UserRole | None = None
    status: ProjectAssignmentStatus | None = None


class ProjectUserAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    user_id: int
    role: UserRole
    status: ProjectAssignmentStatus
    assigned_at: datetime
    removed_at: datetime | None


class ProjectConfigurationUpdate(BaseModel):
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    default_zone: str | None = Field(default=None, max_length=100)
    progress_update_frequency: str | None = Field(default=None, pattern="^(DAILY|WEEKLY)$")
    evidence_required: bool | None = None


class ProjectConfigurationResponse(ProjectConfigurationUpdate):
    model_config = ConfigDict(from_attributes=True)
    project_id: int
    timezone: str
    progress_update_frequency: str
    evidence_required: bool


class ProjectZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)


class ProjectZoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    active: bool | None = None


class ProjectZoneResponse(ProjectZoneCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    active: bool
    created_at: datetime


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class AdminOverview(BaseModel):
    project: AdminProjectResponse
    users_count: int
    active_activities: int
    pending_evidence: int
    open_safety_incidents: int
    open_quality_defects: int
    active_disruptions: int
    low_stock_materials: int


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int | None
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    created_at: datetime
