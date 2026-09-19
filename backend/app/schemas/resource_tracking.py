from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.resource_tracking import MaterialMovementType, VehicleStatus, VehicleTripStatus, EquipmentStatus, EquipmentIssueSeverity

class MaterialCreate(BaseModel):
    name: str
    material_code: str | None = None
    unit: str
    planned_quantity: Decimal | None = Field(None, ge=0)
    minimum_stock_level: Decimal = Field(0, ge=0)
    contract_number: str | None = None

class MaterialResponse(MaterialCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    current_quantity: Decimal
    created_at: datetime

class MovementCreate(BaseModel):
    material_id: int = Field(gt=0)
    movement_type: MaterialMovementType
    quantity: Decimal = Field(gt=0)
    source: str | None = None
    destination: str | None = None
    vehicle_id: int | None = Field(None, gt=0)
    driver_id: int | None = Field(None, gt=0)
    activity_id: int | None = Field(None, gt=0)
    zone: str | None = None
    movement_time: datetime
    notes: str | None = None

class MovementResponse(MovementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    created_by: int | None
    created_at: datetime

class VehicleCreate(BaseModel):
    vehicle_number: str
    vehicle_type: str
    status: VehicleStatus = VehicleStatus.AVAILABLE

class VehicleResponse(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    current_latitude: Decimal | None
    current_longitude: Decimal | None
    created_at: datetime

class TripCreate(BaseModel):
    vehicle_id: int = Field(gt=0)
    driver_id: int = Field(gt=0)
    source: str | None = None
    destination: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    status: VehicleTripStatus = VehicleTripStatus.PLANNED
    material_movement_id: int | None = Field(None, gt=0)
    start_latitude: Decimal | None = Field(None, ge=-90, le=90)
    start_longitude: Decimal | None = Field(None, ge=-180, le=180)
    end_latitude: Decimal | None = Field(None, ge=-90, le=90)
    end_longitude: Decimal | None = Field(None, ge=-180, le=180)

class TripResponse(TripCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    latest_latitude: Decimal | None
    latest_longitude: Decimal | None
    latest_location_time: datetime | None
    created_at: datetime

class LocationUpdate(BaseModel):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    timestamp: datetime

class EquipmentCreate(BaseModel):
    name: str
    equipment_code: str | None = None
    equipment_type: str
    status: EquipmentStatus = EquipmentStatus.AVAILABLE

class EquipmentResponse(EquipmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    current_latitude: Decimal | None
    current_longitude: Decimal | None
    zone: str | None
    created_at: datetime

class EquipmentAssign(BaseModel):
    activity_id: int = Field(gt=0)
    zone: str | None = None
    assigned_from: datetime
    assigned_until: datetime | None = None

class EquipmentIssueCreate(BaseModel):
    activity_id: int | None = Field(None, gt=0)
    issue_type: str
    severity: EquipmentIssueSeverity
    description: str
    reported_at: datetime

class EquipmentIssueResponse(EquipmentIssueCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    equipment_id: int
    reported_by: int | None
    created_at: datetime
