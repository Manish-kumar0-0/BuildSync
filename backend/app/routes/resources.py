from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.notification import NotificationPriority, NotificationType
from app.models.construction_event import ConstructionEventType
from app.models.resource_tracking import (
    Equipment, EquipmentAssignment, EquipmentIssue, EquipmentIssueSeverity,
    EquipmentStatus, MaterialItem, MaterialMovement, MaterialMovementType,
    Vehicle, VehicleStatus, VehicleTrip,
)
from app.routes.events import _activity, _assigned_activity_ids
from app.schemas.resource_tracking import (
    EquipmentAssign, EquipmentCreate, EquipmentIssueCreate, EquipmentIssueResponse,
    EquipmentResponse, LocationUpdate, MaterialCreate, MaterialResponse,
    MovementCreate, MovementResponse, TripCreate, TripResponse, VehicleCreate,
    VehicleResponse,
)
from app.services.events.event_service import create_event
from app.services.notifications.notification_service import (
    notify_resource_issue,
)

router = APIRouter(tags=["resources"])
MANAGEMENT = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
RESOURCE_MANAGERS = MANAGEMENT | {UserRole.SITE_ENGINEER, UserRole.FIELD_ENGINEER,
                                  UserRole.MATERIAL_MANAGER, UserRole.EQUIPMENT_MANAGER}


def _project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")


def _project_access(db: Session, project_id: int, user: User, manage: bool = False) -> None:
    _project(db, project_id)
    if user.role in MANAGEMENT:
        return
    assigned = _assigned_activity_ids(db, user.id, project_id)
    if manage and user.role not in RESOURCE_MANAGERS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    if not assigned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project")


def _activity_in_project(db: Session, project_id: int, activity_id: int | None, user: User) -> None:
    if activity_id is None:
        return
    activity = _activity(db, activity_id)
    if activity.project_id != project_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity does not belong to this project")
    if user.role not in RESOURCE_MANAGERS and activity_id not in _assigned_activity_ids(db, user.id, project_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")


def _material(db: Session, project_id: int, material_id: int) -> MaterialItem:
    item = db.get(MaterialItem, material_id)
    if item is None or item.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    return item


@router.post("/api/projects/{project_id}/materials", response_model=MaterialResponse, status_code=201)
def create_material(project_id: int, data: MaterialCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user, manage=True)
    item = MaterialItem(project_id=project_id, **data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.get("/api/projects/{project_id}/materials", response_model=list[MaterialResponse])
def list_materials(project_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user)
    return db.scalars(select(MaterialItem).where(MaterialItem.project_id == project_id).order_by(MaterialItem.name)).all()


@router.post("/api/projects/{project_id}/materials/movements", response_model=MovementResponse, status_code=201)
def create_movement(project_id: int, data: MovementCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user, manage=True)
    item = _material(db, project_id, data.material_id)
    _activity_in_project(db, project_id, data.activity_id, current_user)
    if data.vehicle_id is not None:
        vehicle = db.get(Vehicle, data.vehicle_id)
        if vehicle is None or vehicle.project_id != project_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Vehicle does not belong to project")
    if data.driver_id is not None:
        driver = db.get(User, data.driver_id)
        if driver is None or not driver.is_active or driver.role != UserRole.DRIVER:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid driver")
    delta = data.quantity if data.movement_type in {MaterialMovementType.RECEIVED, MaterialMovementType.RETURNED} else -data.quantity
    if data.movement_type == MaterialMovementType.ADJUSTMENT:
        delta = data.quantity
    if item.current_quantity + delta < 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Movement would make stock negative")
    movement = MaterialMovement(project_id=project_id, created_by=current_user.id, **data.model_dump())
    item.current_quantity += delta
    db.add(movement); db.flush()
    event_type = {
        MaterialMovementType.RECEIVED: ConstructionEventType.MATERIAL_RECEIVED,
        MaterialMovementType.DISPATCHED: ConstructionEventType.MATERIAL_DISPATCHED,
    }.get(data.movement_type, ConstructionEventType.SYSTEM_EVENT)
    create_event(db, project_id=project_id, activity_id=data.activity_id, event_type=event_type,
                 title=f"Material {data.movement_type.value.lower()}",
                 description=data.notes, actor_user_id=current_user.id,
                 event_timestamp=data.movement_time,
                 metadata={"material_id": item.id, "material_name": item.name,
                           "quantity": str(data.quantity), "unit": item.unit},
                 reference_type="material_movement", reference_id=movement.id)
    if item.current_quantity <= item.minimum_stock_level:
        notify_resource_issue(
            db,
            project_id=project_id,
            entity_id=item.id,
            notification_type=NotificationType.MATERIAL,
            title="Material stock is critical" if item.current_quantity <= 0 else "Material stock is low",
            message=f"{item.name} has {item.current_quantity} {item.unit} remaining.",
            roles={UserRole.MATERIAL_MANAGER, UserRole.PROJECT_MANAGER, UserRole.ADMIN},
            priority=NotificationPriority.CRITICAL if item.current_quantity <= 0 else NotificationPriority.HIGH,
            entity_type="material_stock_critical" if item.current_quantity <= 0 else "material_stock_low",
        )
    db.commit(); db.refresh(movement)
    return movement


@router.get("/api/projects/{project_id}/materials/{material_id}/history", response_model=list[MovementResponse])
def material_history(project_id: int, material_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user); _material(db, project_id, material_id)
    return db.scalars(select(MaterialMovement).where(MaterialMovement.project_id == project_id,
        MaterialMovement.material_id == material_id).order_by(MaterialMovement.movement_time.asc(), MaterialMovement.id.asc())).all()


@router.get("/api/projects/{project_id}/materials/summary")
def material_summary(project_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user)
    items = db.scalars(select(MaterialItem).where(MaterialItem.project_id == project_id)).all()
    return {"materials": [{"material_id": i.id, "name": i.name, "unit": i.unit,
        "current_quantity": i.current_quantity, "minimum_stock_level": i.minimum_stock_level,
        "stock_status": "CRITICAL" if i.current_quantity <= 0 else
        ("LOW" if i.current_quantity < i.minimum_stock_level else "NORMAL")} for i in items]}


@router.post("/api/projects/{project_id}/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle(project_id: int, data: VehicleCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user, manage=True)
    vehicle = Vehicle(project_id=project_id, **data.model_dump())
    db.add(vehicle); db.commit(); db.refresh(vehicle); return vehicle


@router.post("/api/projects/{project_id}/vehicle-trips", response_model=TripResponse, status_code=201)
def create_trip(project_id: int, data: TripCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user, manage=True)
    vehicle = db.get(Vehicle, data.vehicle_id)
    driver = db.get(User, data.driver_id)
    if vehicle is None or vehicle.project_id != project_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Vehicle does not belong to project")
    if driver is None or not driver.is_active or driver.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid driver")
    if data.end_time is not None and data.end_time < data.start_time:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "end_time must not precede start_time")
    trip = VehicleTrip(project_id=project_id, **data.model_dump())
    db.add(trip); vehicle.status = VehicleStatus.IN_TRANSIT if data.status.value == "IN_TRANSIT" else vehicle.status
    db.commit(); db.refresh(trip); return trip


@router.get("/api/projects/{project_id}/vehicle-trips", response_model=list[TripResponse])
def list_trips(project_id: int, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    query = select(VehicleTrip).where(VehicleTrip.project_id == project_id)
    if current_user.role == UserRole.DRIVER:
        _project(db, project_id)
        query = query.where(VehicleTrip.driver_id == current_user.id)
    else:
        _project_access(db, project_id, current_user)
    return db.scalars(query.order_by(VehicleTrip.start_time.desc())).all()


@router.get("/api/vehicle-trips/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    trip = db.get(VehicleTrip, trip_id)
    if trip is None: raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    _project_access(db, trip.project_id, current_user); return trip


@router.post("/api/vehicle-trips/{trip_id}/location", response_model=TripResponse)
def update_trip_location(trip_id: int, data: LocationUpdate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    trip = db.get(VehicleTrip, trip_id)
    if trip is None: raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    _project_access(db, trip.project_id, current_user, manage=True)
    trip.latest_latitude, trip.latest_longitude, trip.latest_location_time = data.latitude, data.longitude, data.timestamp
    db.commit(); db.refresh(trip); return trip


@router.post("/api/projects/{project_id}/equipment", response_model=EquipmentResponse, status_code=201)
def create_equipment(project_id: int, data: EquipmentCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user, manage=True)
    item = Equipment(project_id=project_id, **data.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item


@router.post("/api/projects/{project_id}/equipment/{equipment_id}/assign")
def assign_equipment(project_id: int, equipment_id: int, data: EquipmentAssign,
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user, manage=True)
    equipment = db.get(Equipment, equipment_id)
    if equipment is None or equipment.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found")
    _activity_in_project(db, project_id, data.activity_id, current_user)
    assignment = EquipmentAssignment(project_id=project_id, equipment_id=equipment_id,
                                     assigned_by=current_user.id, **data.model_dump())
    equipment.status = EquipmentStatus.IN_USE
    db.add(assignment); db.commit(); db.refresh(assignment)
    return assignment


@router.get("/api/projects/{project_id}/equipment/assignments")
def equipment_assignments(project_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user)
    return db.scalars(select(EquipmentAssignment).where(EquipmentAssignment.project_id == project_id)
                      .order_by(EquipmentAssignment.assigned_from.desc())).all()


@router.post("/api/equipment/{equipment_id}/issues", response_model=EquipmentIssueResponse, status_code=201)
def create_equipment_issue(equipment_id: int, data: EquipmentIssueCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    equipment = db.get(Equipment, equipment_id)
    if equipment is None: raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found")
    _project_access(db, equipment.project_id, current_user, manage=True)
    _activity_in_project(db, equipment.project_id, data.activity_id, current_user)
    issue = EquipmentIssue(project_id=equipment.project_id, equipment_id=equipment_id,
                           reported_by=current_user.id, **data.model_dump())
    equipment.status = EquipmentStatus.OUT_OF_SERVICE if data.severity in {EquipmentIssueSeverity.HIGH, EquipmentIssueSeverity.CRITICAL} else EquipmentStatus.MAINTENANCE
    db.add(issue); db.flush()
    create_event(db, project_id=equipment.project_id, activity_id=data.activity_id,
                 event_type=ConstructionEventType.EQUIPMENT_ISSUE,
                 title=f"Equipment issue: {data.issue_type}", description=data.description,
                 actor_user_id=current_user.id, event_timestamp=data.reported_at,
                 metadata={"equipment_id": equipment.id, "severity": data.severity.value},
                 reference_type="equipment_issue", reference_id=issue.id)
    if data.severity in {EquipmentIssueSeverity.HIGH, EquipmentIssueSeverity.CRITICAL}:
        notify_resource_issue(
            db,
            project_id=equipment.project_id,
            entity_id=issue.id,
            notification_type=NotificationType.EQUIPMENT,
            title="Equipment issue reported",
            message=data.description,
            roles={UserRole.EQUIPMENT_MANAGER, UserRole.PROJECT_MANAGER, UserRole.ADMIN},
            priority=NotificationPriority.CRITICAL if data.severity == EquipmentIssueSeverity.CRITICAL else NotificationPriority.HIGH,
        )
    db.commit(); db.refresh(issue); return issue


@router.get("/api/projects/{project_id}/equipment", response_model=list[EquipmentResponse])
def list_equipment(project_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    _project_access(db, project_id, current_user)
    return db.scalars(select(Equipment).where(Equipment.project_id == project_id).order_by(Equipment.name)).all()


@router.get("/api/activities/{activity_id}/resources")
def activity_resources(activity_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    activity = _activity(db, activity_id)
    if current_user.role not in MANAGEMENT and activity_id not in _assigned_activity_ids(db, current_user.id, activity.project_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
    materials = db.scalars(select(MaterialItem).where(MaterialItem.project_id == activity.project_id,
        MaterialItem.current_quantity > 0)).all()
    assignments = db.scalars(select(EquipmentAssignment).where(EquipmentAssignment.activity_id == activity_id)).all()
    equipment = [db.get(Equipment, a.equipment_id) for a in assignments]
    return {"activity_id": activity_id, "materials": materials, "equipment": [e for e in equipment if e],
            "material_status": "AVAILABLE" if materials else "UNAVAILABLE",
            "equipment_status": "AVAILABLE" if any(e and e.status not in {EquipmentStatus.OUT_OF_SERVICE, EquipmentStatus.MAINTENANCE} for e in equipment) else "UNAVAILABLE"}
