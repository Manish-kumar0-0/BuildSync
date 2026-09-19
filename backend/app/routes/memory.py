from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity
from app.models.project_memory import MemoryImportance, MemoryType, ProjectMemory
from app.schemas.memory import (
    MemoryContextResponse,
    MemoryEventResponse,
    ProjectMemoryDetailResponse,
    ProjectMemoryListResponse,
    ProjectMemoryResponse,
)
from app.routes.events import _activity, _assigned_activity_ids

router = APIRouter(tags=["project memory"])
MANAGEMENT_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}


def _project_access(
    db: Session, project_id: int, user: User
) -> set[int] | None:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if user.role in MANAGEMENT_ROLES:
        return None
    activity_ids = _assigned_activity_ids(db, user.id, project_id)
    if not activity_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project memory")
    return activity_ids


def _memory_query(project_id: int, activity_ids: set[int] | None):
    query = (
        select(ProjectMemory)
        .options(
            selectinload(ProjectMemory.event),
            selectinload(ProjectMemory.activity).selectinload(Activity.wbs),
        )
        .where(ProjectMemory.project_id == project_id)
    )
    if activity_ids is not None:
        query = query.where(ProjectMemory.activity_id.in_(activity_ids))
    return query


def _memory_response(memory: ProjectMemory) -> ProjectMemoryResponse:
    return ProjectMemoryResponse(
        id=memory.id,
        project_id=memory.project_id,
        event_id=memory.event_id,
        activity_id=memory.activity_id,
        type=memory.memory_type,
        importance=memory.importance,
        title=memory.title,
        summary=memory.summary,
        memory_date=memory.memory_date,
        source_type=memory.source_type,
        source_id=memory.source_id,
        metadata=memory.event_metadata,
    )


@router.get(
    "/api/projects/{project_id}/memory",
    response_model=ProjectMemoryListResponse,
)
def list_project_memory(
    project_id: int,
    memory_type: MemoryType | None = None,
    importance: MemoryImportance | None = None,
    activity_id: int | None = Query(None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity_ids = _project_access(db, project_id, current_user)
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "start_date must not exceed end_date")
    query = _memory_query(project_id, activity_ids)
    if activity_id is not None:
        query = query.where(ProjectMemory.activity_id == activity_id)
    if memory_type is not None:
        query = query.where(ProjectMemory.memory_type == memory_type)
    if importance is not None:
        query = query.where(ProjectMemory.importance == importance)
    if start_date is not None:
        query = query.where(ProjectMemory.memory_date >= start_date)
    if end_date is not None:
        query = query.where(ProjectMemory.memory_date <= end_date)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(ProjectMemory.title.ilike(pattern), ProjectMemory.summary.ilike(pattern))
        )
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    memories = list(
        db.scalars(
            query.order_by(ProjectMemory.memory_date.desc(), ProjectMemory.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {
        "project_id": project_id,
        "total": total,
        "memories": [_memory_response(memory) for memory in memories],
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/api/projects/{project_id}/memory/context",
    response_model=MemoryContextResponse,
)
def memory_context(
    project_id: int,
    activity_id: int | None = Query(None, gt=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    activity_ids = _project_access(db, project_id, current_user)
    query = _memory_query(project_id, activity_ids)
    if activity_id is not None:
        query = query.where(ProjectMemory.activity_id == activity_id)
    memories = list(
        db.scalars(
            query.order_by(ProjectMemory.memory_date.desc(), ProjectMemory.id.desc())
            .limit(limit)
        ).all()
    )
    return {
        "project_id": project_id,
        "context": [
            {
                "date": memory.memory_date,
                "type": memory.memory_type,
                "summary": memory.summary,
            }
            for memory in memories
        ],
    }


@router.get(
    "/api/projects/{project_id}/memory/{memory_id}",
    response_model=ProjectMemoryDetailResponse,
)
def memory_detail(
    project_id: int,
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectMemoryDetailResponse:
    activity_ids = _project_access(db, project_id, current_user)
    memory = db.scalar(
        _memory_query(project_id, activity_ids).where(ProjectMemory.id == memory_id)
    )
    if memory is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project memory not found")
    event = memory.event
    payload = _memory_response(memory).model_dump()
    payload["event"] = MemoryEventResponse(
        id=event.id,
        event_type=event.event_type.value,
        event_timestamp=event.event_timestamp,
        title=event.title,
        description=event.description,
        latitude=event.latitude,
        longitude=event.longitude,
        gps_accuracy=event.gps_accuracy,
        zone=event.zone,
        evidence_id=event.evidence_id,
    )
    payload["activity_name"] = memory.activity.name if memory.activity else None
    payload["wbs_id"] = memory.activity.wbs_id if memory.activity else None
    payload["wbs_name"] = (
        memory.activity.wbs.name
        if memory.activity is not None and memory.activity.wbs is not None
        else None
    )
    return ProjectMemoryDetailResponse.model_validate(payload)


@router.get(
    "/api/activities/{activity_id}/memory",
    response_model=list[ProjectMemoryResponse],
)
def activity_memory(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectMemoryResponse]:
    activity = _activity(db, activity_id)
    if current_user.role not in MANAGEMENT_ROLES and not _assigned_activity_ids(
        db, current_user.id, activity.project_id
    ).intersection({activity_id}):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity memory")
    memories = db.scalars(
        _memory_query(activity.project_id, {activity_id}).where(
            ProjectMemory.activity_id == activity_id
        ).order_by(ProjectMemory.memory_date.asc(), ProjectMemory.id.asc())
    ).all()
    return [_memory_response(memory) for memory in memories]
