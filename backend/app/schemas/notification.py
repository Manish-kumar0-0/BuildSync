from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationPriority, NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    recipient_user_id: int
    activity_id: int | None
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    reference_type: str | None
    reference_id: int | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    page: int
    page_size: int
    total: int


class UnreadCountResponse(BaseModel):
    unread_count: int
