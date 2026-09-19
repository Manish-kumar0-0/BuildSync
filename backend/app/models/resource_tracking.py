import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MaterialMovementType(str, enum.Enum):
    RECEIVED = "RECEIVED"
    DISPATCHED = "DISPATCHED"
    TRANSFERRED = "TRANSFERRED"
    CONSUMED = "CONSUMED"
    RETURNED = "RETURNED"
    ADJUSTMENT = "ADJUSTMENT"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_TRANSIT = "IN_TRANSIT"
    ON_SITE = "ON_SITE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class VehicleTripStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EquipmentStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class EquipmentIssueSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaterialItem(Base):
    __tablename__ = "material_items"
    __table_args__ = (Index("ix_material_items_project_name", "project_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[str | None] = mapped_column(String(100), index=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    planned_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0, nullable=False)
    minimum_stock_level: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0, nullable=False)
    contract_number: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    vehicle_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(Enum(VehicleStatus, name="vehicle_status"), default=VehicleStatus.AVAILABLE, nullable=False, index=True)
    current_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    current_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaterialMovement(Base):
    __tablename__ = "material_movements"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_material_movement_quantity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material_items.id", ondelete="CASCADE"), index=True)
    movement_type: Mapped[MaterialMovementType] = mapped_column(Enum(MaterialMovementType, name="material_movement_type"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), index=True)
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    movement_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VehicleTrip(Base):
    __tablename__ = "vehicle_trips"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    source: Mapped[str | None] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[VehicleTripStatus] = mapped_column(Enum(VehicleTripStatus, name="vehicle_trip_status"), default=VehicleTripStatus.PLANNED, nullable=False, index=True)
    material_movement_id: Mapped[int | None] = mapped_column(ForeignKey("material_movements.id", ondelete="SET NULL"))
    start_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    start_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    end_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    end_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latest_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    latest_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latest_location_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_code: Mapped[str | None] = mapped_column(String(100), index=True)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[EquipmentStatus] = mapped_column(Enum(EquipmentStatus, name="equipment_status"), default=EquipmentStatus.AVAILABLE, nullable=False, index=True)
    current_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    current_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EquipmentUsageRecord(Base):
    __tablename__ = "equipment_usage_records"
    __table_args__ = (Index("ix_equipment_usage_project_period", "project_id", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    equipment = relationship("Equipment")
    activity = relationship("Activity")
    recorder = relationship("User")


class EquipmentAssignment(Base):
    __tablename__ = "equipment_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    zone: Mapped[str | None] = mapped_column(String(100), index=True)
    assigned_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EquipmentIssue(Base):
    __tablename__ = "equipment_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), index=True)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[EquipmentIssueSeverity] = mapped_column(Enum(EquipmentIssueSeverity, name="equipment_issue_severity"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reported_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
