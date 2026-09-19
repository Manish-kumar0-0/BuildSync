from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.services.assistant.assistant_service import (
    AssistantConfigurationError,
    AssistantProviderError,
    generate_project_answer,
)
from app.services.assistant.context_service import build_project_context
from app.routes.events import _activity, _assigned_activity_ids

router = APIRouter(tags=["project assistant"])
MANAGEMENT_ROLES = {UserRole.PROJECT_MANAGER, UserRole.ADMIN}


def _authorize(
    db: Session, project_id: int, activity_id: int | None, user: User
) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if activity_id is not None:
        activity = _activity(db, activity_id)
        if activity.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")
        if user.role in MANAGEMENT_ROLES:
            return
        if activity_id not in _assigned_activity_ids(db, user.id, project_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this activity")
        return
    if user.role in MANAGEMENT_ROLES:
        return
    if user.role == UserRole.SITE_ENGINEER and _assigned_activity_ids(
        db, user.id, project_id
    ):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not authorized for this project assistant")


@router.post(
    "/api/projects/{project_id}/assistant",
    response_model=AssistantResponse,
)
@router.post(
    "/api/projects/{project_id}/assistant/query",
    response_model=AssistantResponse,
)
def project_assistant(
    project_id: int,
    request: AssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantResponse:
    _authorize(db, project_id, request.activity_id, current_user)
    context = build_project_context(
        db,
        project_id,
        request.question,
        request.activity_id,
    )
    try:
        result = generate_project_answer(request.question, context)
    except AssistantConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except AssistantProviderError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Project Assistant provider could not complete the request",
        ) from exc
    source_ids = set(result.source_ids)
    return AssistantResponse(
        question=request.question or request.message or "",
        answer=result.answer,
        intent=context.intent,
        sources=[source for source in context.sources if source.id in source_ids]
        if source_ids
        else context.sources,
        confidence=result.confidence,
    )
