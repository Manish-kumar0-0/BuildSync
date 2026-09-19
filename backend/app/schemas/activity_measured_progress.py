from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.activity_measured_progress import MeasuredProgressVerificationStatus


class MeasuredProgressCreate(BaseModel):
    assessment_date: date
    planned_quantity: Decimal = Field(gt=0)
    completed_quantity: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def completed_does_not_exceed_planned(self) -> "MeasuredProgressCreate":
        if self.completed_quantity > self.planned_quantity:
            raise ValueError("completed_quantity cannot exceed planned_quantity")
        return self


class MeasuredProgressVerification(BaseModel):
    decision: MeasuredProgressVerificationStatus
    notes: str | None = Field(default=None, max_length=2000)


class MeasuredProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    activity_id: int
    assessment_date: date
    planned_quantity: Decimal
    completed_quantity: Decimal
    unit: str
    notes: str | None
    verification_status: MeasuredProgressVerificationStatus
    recorded_by: int
    verified_by: int | None
    verification_notes: str | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
