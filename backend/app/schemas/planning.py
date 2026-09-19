from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.planning import ActivityStatus, ProjectStatus, WBSStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    project_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    client: str | None = None
    location: str | None = None
    package_name: str | None = None
    start_date: date
    planned_end_date: date
    status: ProjectStatus = ProjectStatus.PLANNING

    @model_validator(mode="after")
    def valid_dates(self) -> "ProjectCreate":
        if self.planned_end_date < self.start_date:
            raise ValueError("planned_end_date cannot be before start_date")
        return self


class ProjectUpdate(BaseModel):
    project_code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    client: str | None = None
    location: str | None = None
    package_name: str | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    status: ProjectStatus | None = None


class ProjectResponse(ORMModel, ProjectCreate):
    id: int
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class WBSCreate(BaseModel):
    wbs_code: str = Field(min_length=1, max_length=50)
    parent_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    level: int = Field(ge=0)
    status: WBSStatus = WBSStatus.PLANNED


class WBSUpdate(BaseModel):
    wbs_code: str | None = Field(default=None, min_length=1, max_length=50)
    parent_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    level: int | None = Field(default=None, ge=0)
    status: WBSStatus | None = None


class WBSResponse(ORMModel, WBSCreate):
    id: int
    project_id: int
    created_at: datetime


class BOQCreate(BaseModel):
    wbs_id: int | None = Field(default=None, gt=0)
    item_code: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)
    unit: str = Field(min_length=1, max_length=30)
    planned_quantity: Decimal = Field(ge=0, max_digits=16, decimal_places=3)
    rate: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    planned_cost: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class BOQUpdate(BaseModel):
    wbs_id: int | None = Field(default=None, gt=0)
    item_code: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=1)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    planned_quantity: Decimal | None = Field(default=None, ge=0)
    rate: Decimal | None = Field(default=None, ge=0)
    planned_cost: Decimal | None = Field(default=None, ge=0)


class BOQResponse(ORMModel, BOQCreate):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class ScheduleCreate(BaseModel):
    wbs_id: int | None = Field(default=None, gt=0)
    boq_item_id: int | None = Field(default=None, gt=0)
    activity_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    planned_start: date
    planned_finish: date
    planned_quantity: Decimal = Field(ge=0, max_digits=16, decimal_places=3)
    planned_progress: Decimal = Field(default=0, ge=0, le=100)
    weightage: Decimal = Field(default=0, ge=0, le=100)
    status: ActivityStatus = ActivityStatus.NOT_STARTED

    @model_validator(mode="after")
    def valid_dates(self) -> "ScheduleCreate":
        if self.planned_finish < self.planned_start:
            raise ValueError("planned_finish cannot be before planned_start")
        return self


class ScheduleUpdate(BaseModel):
    wbs_id: int | None = Field(default=None, gt=0)
    boq_item_id: int | None = Field(default=None, gt=0)
    activity_code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    planned_start: date | None = None
    planned_finish: date | None = None
    planned_quantity: Decimal | None = Field(default=None, ge=0)
    planned_progress: Decimal | None = Field(default=None, ge=0, le=100)
    weightage: Decimal | None = Field(default=None, ge=0, le=100)
    status: ActivityStatus | None = None


class ScheduleResponse(ORMModel, ScheduleCreate):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class PlannedProgressCreate(BaseModel):
    date: date
    planned_percentage: Decimal = Field(ge=0, le=100)
    planned_quantity: Decimal = Field(ge=0)


class PlannedProgressResponse(ORMModel, PlannedProgressCreate):
    id: int
    schedule_activity_id: int


class PlanSummary(BaseModel):
    project: ProjectResponse
    total_wbs_items: int
    total_boq_items: int
    total_schedule_activities: int
    overall_planned_progress: Decimal
    activities_by_status: dict[str, int]
    upcoming_activities: list[ScheduleResponse]
    delayed_activities: list[ScheduleResponse]
