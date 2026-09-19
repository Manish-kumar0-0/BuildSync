from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notifications.notification_service import (
    get_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(tags=["notifications"])
PROJECT_NOTIFICATION_ROLES = {
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
    UserRole.ADMIN,
}


@router.get("/api/notifications", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = False,
    priority: NotificationPriority | None = None,
    notification_type: NotificationType | None = Query(None, alias="type"),
    project_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    items, total = get_user_notifications(
        db,
        current_user.id,
        unread_only=unread_only,
        priority=priority,
        notification_type=notification_type,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/api/notifications/unread-count", response_model=UnreadCountResponse)
def unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    count = db.scalar(
        select(func.count()).where(
            Notification.recipient_user_id == current_user.id,
            Notification.is_read.is_(False),
        )
    ) or 0
    return {"unread_count": count}


@router.get("/api/notifications/unread", response_model=NotificationListResponse)
def list_unread_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    items, total = get_user_notifications(
        db,
        current_user.id,
        unread_only=True,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.patch("/api/notifications/read-all", response_model=dict[str, int])
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    return {"marked_read": mark_all_notifications_read(db, current_user.id)}


@router.patch(
    "/api/notifications/{notification_id}/read",
    response_model=NotificationResponse,
)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Notification:
    notification = mark_notification_read(db, notification_id, current_user.id)
    if notification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return notification


@router.get(
    "/api/projects/{project_id}/notifications",
    response_model=NotificationListResponse,
)
def list_project_notifications(
    project_id: int,
    unread_only: bool = False,
    priority: NotificationPriority | None = None,
    notification_type: NotificationType | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    authorized_site_engineer = current_user.role == UserRole.SITE_ENGINEER and db.scalar(
        select(ActivityAssignment.id)
        .join(Activity, Activity.id == ActivityAssignment.activity_id)
        .where(
            Activity.project_id == project_id,
            ActivityAssignment.user_id == current_user.id,
            ActivityAssignment.status == AssignmentStatus.ACTIVE,
        )
    ) is not None
    if current_user.role not in {UserRole.PROJECT_MANAGER, UserRole.ADMIN} and not authorized_site_engineer:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view project notifications",
        )
    items, total = get_user_notifications(
        db,
        current_user.id,
        unread_only=unread_only,
        priority=priority,
        notification_type=notification_type,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "page": page, "page_size": page_size, "total": total}
