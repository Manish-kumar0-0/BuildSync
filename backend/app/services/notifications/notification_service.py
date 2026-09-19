from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ProjectAssignmentStatus,
    ProjectUserAssignment,
    User,
    UserRole,
)
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus
from app.models.planning import Project
from app.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)


def create_notification(
    db: Session,
    *,
    recipient_user_id: int,
    project_id: int,
    activity_id: int | None,
    notification_type: NotificationType,
    priority: NotificationPriority,
    title: str,
    message: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> Notification | None:
    if db.get(Project, project_id) is None:
        raise ValueError("Project not found")
    recipient = db.get(User, recipient_user_id)
    if recipient is None or not recipient.is_active:
        raise ValueError("Recipient user is invalid")
    if not isinstance(notification_type, NotificationType):
        raise ValueError("Invalid notification type")
    if not isinstance(priority, NotificationPriority):
        raise ValueError("Invalid notification priority")
    duplicate = db.scalar(
        select(Notification).where(
            Notification.project_id == project_id,
            Notification.activity_id == activity_id,
            Notification.recipient_user_id == recipient_user_id,
            Notification.type == notification_type,
            Notification.reference_type == reference_type,
            Notification.reference_id == reference_id,
        )
    )
    if duplicate is not None:
        return None
    notification = Notification(
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        activity_id=activity_id,
        type=notification_type,
        priority=priority,
        title=title,
        message=message,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(notification)
    db.flush()
    return notification


def get_user_notifications(
    db: Session,
    user_id: int,
    *,
    unread_only: bool = False,
    priority: NotificationPriority | None = None,
    notification_type: NotificationType | None = None,
    project_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Notification], int]:
    query = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    if priority is not None:
        query = query.where(Notification.priority == priority)
    if notification_type is not None:
        query = query.where(Notification.type == notification_type)
    if project_id is not None:
        query = query.where(Notification.project_id == project_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def mark_notification_read(
    db: Session, notification_id: int, user_id: int
) -> Notification | None:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
        )
    )
    if notification is None:
        return None
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id: int) -> int:
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
        ).all()
    )
    now = datetime.now(timezone.utc)
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
    db.commit()
    return len(notifications)


def project_notification_recipients(
    db: Session, project_id: int, activity: Activity | None = None
) -> list[int]:
    return project_notification_recipients_for_roles(
        db,
        project_id,
        {
            UserRole.ADMIN,
            UserRole.PROJECT_MANAGER,
            UserRole.SITE_ENGINEER,
            UserRole.FIELD_ENGINEER,
        },
        activity=activity,
    )


def project_notification_recipients_for_roles(
    db: Session,
    project_id: int,
    roles: set[UserRole],
    *,
    activity: Activity | None = None,
) -> list[int]:
    user_ids = set(
        db.scalars(
            select(ProjectUserAssignment.user_id)
            .join(User, User.id == ProjectUserAssignment.user_id)
            .where(
                ProjectUserAssignment.project_id == project_id,
                ProjectUserAssignment.status == ProjectAssignmentStatus.ACTIVE,
                User.is_active.is_(True),
                User.role.in_(roles),
            )
        ).all()
    )
    project = db.get(Project, project_id)
    if project is not None and project.created_by is not None:
        creator = db.get(User, project.created_by)
        if creator is not None and creator.is_active and creator.role in roles:
            user_ids.add(creator.id)
    if activity is not None:
        user_ids.update(
            db.scalars(
                select(ActivityAssignment.user_id)
                .join(User, User.id == ActivityAssignment.user_id)
                .where(
                    ActivityAssignment.activity_id == activity.id,
                    ActivityAssignment.status == AssignmentStatus.ACTIVE,
                    User.role.in_(
                        list(roles)
                    ),
                    User.is_active.is_(True),
                )
            ).all()
        )
    return list(user_ids)


def _notify_roles(
    db: Session,
    *,
    project_id: int,
    roles: set[UserRole],
    notification_type: NotificationType,
    priority: NotificationPriority,
    title: str,
    message: str,
    entity_type: str,
    entity_id: int,
    activity: Activity | None = None,
) -> None:
    for recipient in project_notification_recipients_for_roles(
        db, project_id, roles, activity=activity
    ):
        create_notification(
            db,
            recipient_user_id=recipient,
            project_id=project_id,
            activity_id=activity.id if activity else None,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            reference_type=entity_type,
            reference_id=entity_id,
        )


def notify_safety_incident(db: Session, incident, activity: Activity | None = None) -> None:
    if incident.severity.value not in {"HIGH", "CRITICAL"}:
        return
    roles = {UserRole.SAFETY_OFFICER, UserRole.PROJECT_MANAGER, UserRole.ADMIN}
    priority = (
        NotificationPriority.CRITICAL
        if incident.severity.value == "CRITICAL"
        else NotificationPriority.HIGH
    )
    _notify_roles(
        db,
        project_id=incident.project_id,
        roles=roles,
        notification_type=NotificationType.SAFETY,
        priority=priority,
        title=f"{incident.severity.value.title()} safety incident reported",
        message=incident.description,
        entity_type="safety_incident",
        entity_id=incident.id,
        activity=activity,
    )


def notify_quality_issue(
    db: Session,
    *,
    project_id: int,
    entity_id: int,
    title: str,
    message: str,
    activity: Activity | None = None,
) -> None:
    _notify_roles(
        db,
        project_id=project_id,
        roles={UserRole.QA_QC_ENGINEER, UserRole.PROJECT_MANAGER, UserRole.ADMIN},
        notification_type=NotificationType.QUALITY,
        priority=NotificationPriority.HIGH,
        title=title,
        message=message,
        entity_type="quality_issue",
        entity_id=entity_id,
        activity=activity,
    )


def notify_resource_issue(
    db: Session,
    *,
    project_id: int,
    entity_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    roles: set[UserRole],
    priority: NotificationPriority = NotificationPriority.HIGH,
    entity_type: str = "resource_issue",
) -> None:
    _notify_roles(
        db,
        project_id=project_id,
        roles=roles,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def notify_risk_prediction(db: Session, prediction, activity, assessment_date) -> None:
    recipients = project_notification_recipients(db, activity.project_id, activity)
    if prediction.risk_level.value == "CRITICAL":
        targets = [
            recipient
            for recipient in recipients
            if db.get(User, recipient).role in {UserRole.PROJECT_MANAGER, UserRole.ADMIN}
        ]
        notification_type = NotificationType.CRITICAL_RISK
        priority = NotificationPriority.CRITICAL
        title = "Critical activity risk detected"
        message = (
            f"Activity {activity.name} has reached CRITICAL risk with an estimated "
            f"delay of {prediction.predicted_delay_days or 0} days."
        )
    elif prediction.risk_level.value == "HIGH":
        targets = recipients
        notification_type = NotificationType.HIGH_RISK
        priority = NotificationPriority.HIGH
        title = "High activity risk detected"
        message = f"Activity {activity.name} has reached HIGH risk."
    else:
        targets = []
        notification_type = NotificationType.SYSTEM
        priority = NotificationPriority.LOW
        title = ""
        message = ""
    for recipient in targets:
        create_notification(
            db,
            recipient_user_id=recipient,
            project_id=activity.project_id,
            activity_id=activity.id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            reference_type="ActivityRiskPrediction",
            reference_id=prediction.id,
        )
    if prediction.predicted_delay_days is not None and prediction.predicted_delay_days >= 7:
        for recipient in recipients:
            create_notification(
                db,
                recipient_user_id=recipient,
                project_id=activity.project_id,
                activity_id=activity.id,
                notification_type=NotificationType.ACTIVITY_DELAY,
                priority=NotificationPriority.HIGH,
                title="Activity delay predicted",
                message=(
                    f"{activity.name} may be delayed by approximately "
                    f"{prediction.predicted_delay_days} days."
                ),
                reference_type="ActivityRiskPrediction",
                reference_id=prediction.id,
            )
    schedule = activity.schedule_activity
    if (
        schedule is not None
        and schedule.planned_finish < assessment_date
        and activity.status.value != "COMPLETED"
    ):
        for recipient in recipients:
            create_notification(
                db,
                recipient_user_id=recipient,
                project_id=activity.project_id,
                activity_id=activity.id,
                notification_type=NotificationType.MILESTONE_MISSED,
                priority=NotificationPriority.HIGH,
                title="Milestone missed",
                message=f"Activity {activity.name} is past its planned finish date.",
                reference_type="ActivityRiskPrediction",
                reference_id=prediction.id,
            )
    db.commit()


def notify_recovery_recommendation(db: Session, recommendation, activity) -> None:
    for recipient in project_notification_recipients(db, activity.project_id, activity):
        create_notification(
            db,
            recipient_user_id=recipient,
            project_id=activity.project_id,
            activity_id=activity.id,
            notification_type=NotificationType.RECOVERY_RECOMMENDATION,
            priority=NotificationPriority.HIGH,
            title="Recovery action recommended",
            message=(
                f"BuildSync recommends {recommendation.title.lower()} for "
                f"{activity.name} to help recover lost progress."
            ),
            reference_type="RecoveryRecommendation",
            reference_id=recommendation.id,
        )
    db.commit()


def notify_evidence_event(db: Session, evidence, activity, rejected: bool) -> None:
    recipients = project_notification_recipients(db, activity.project_id, activity)
    if rejected and evidence.uploaded_by is not None:
        recipients.append(evidence.uploaded_by)
    recipients = list(set(recipients))
    notification_type = (
        NotificationType.EVIDENCE_REJECTED
        if rejected
        else NotificationType.EVIDENCE_PENDING
    )
    priority = NotificationPriority.HIGH if rejected else NotificationPriority.MEDIUM
    for recipient in recipients:
        create_notification(
            db,
            recipient_user_id=recipient,
            project_id=activity.project_id,
            activity_id=activity.id,
            notification_type=notification_type,
            priority=priority,
            title="Evidence rejected" if rejected else "Evidence pending verification",
            message=(
                f"Your submitted evidence for {activity.name} was rejected. "
                "Please review the verification feedback."
                if rejected
                else f"Evidence for {activity.name} is pending verification."
            ),
            reference_type="Evidence",
            reference_id=evidence.id,
        )
    db.commit()


def notify_recovery_status(db: Session, recommendation, activity) -> None:
    for recipient in project_notification_recipients(db, activity.project_id, activity):
        create_notification(
            db,
            recipient_user_id=recipient,
            project_id=activity.project_id,
            activity_id=activity.id,
            notification_type=NotificationType.RECOVERY_ACCEPTED,
            priority=NotificationPriority.MEDIUM,
            title="Recovery recommendation accepted",
            message=f"Recovery recommendation for {activity.name} was accepted.",
            reference_type="RecoveryRecommendation",
            reference_id=recommendation.id,
        )
    db.commit()
