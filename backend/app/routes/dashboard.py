from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Project, User, UserRole
from app.models.evidence import Evidence, EvidenceStatus
from app.models.field_activity import Activity, ActivityAssignment, AssignmentStatus, FieldActivityStatus
from app.models.progress_assessment import ProgressAssessment
from app.models.recovery import RecommendationStatus, RecoveryRecommendation
from app.models.risk_prediction import ActivityRiskPrediction, RiskLevel
from app.schemas.dashboard import (
    CombinedTimelineResponse,
    DelaySummaryResponse,
    ProgressTimelineResponse,
    ProgressTrendResponse,
    ProjectDashboardSummary,
    RecoverySummaryResponse,
    RiskTimelineResponse,
)

router = APIRouter(tags=["project dashboard"])
ALLOWED_ROLES = {
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
    UserRole.FIELD_ENGINEER,
    UserRole.ADMIN,
}
TOP_LIMIT = 10


def _decimal(value: Decimal | None) -> Decimal | None:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if value is not None else None


def _can_view_project(db: Session, project_id: int, user: User) -> bool:
    if user.role in {UserRole.PROJECT_MANAGER, UserRole.ADMIN}:
        return True
    if user.role not in {UserRole.SITE_ENGINEER, UserRole.FIELD_ENGINEER}:
        return False
    return db.scalar(
        select(ActivityAssignment.id)
        .join(Activity, Activity.id == ActivityAssignment.activity_id)
        .where(
            Activity.project_id == project_id,
            ActivityAssignment.user_id == user.id,
            ActivityAssignment.status == AssignmentStatus.ACTIVE,
        )
    ) is not None


def _latest_by_activity(items: list[Any]) -> dict[int, Any]:
    latest: dict[int, Any] = {}
    for item in items:
        current = latest.get(item.activity_id)
        if current is None or (
            item.assessment_date,
            item.id,
        ) > (current.assessment_date, current.id):
            latest[item.activity_id] = item
    return latest


def _dashboard_project(
    db: Session, project_id: int, current_user: User
) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if current_user.role not in ALLOWED_ROLES or not _can_view_project(
        db, project_id, current_user
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this project dashboard",
        )
    return project


def _date_range(
    start_date: date | None,
    end_date: date | None,
    available_dates: list[date],
) -> tuple[date | None, date | None]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(422, "start_date cannot be after end_date")
    if start_date is not None or end_date is not None:
        return start_date, end_date
    if not available_dates:
        return None, None
    latest = max(available_dates)
    return max(min(available_dates), latest - timedelta(days=30)), latest


def _progress_points(
    assessments: list[ProgressAssessment],
    weights: dict[int, Decimal | None],
) -> list[dict[str, Any]]:
    by_date: dict[date, dict[int, ProgressAssessment]] = defaultdict(dict)
    for item in assessments:
        current = by_date[item.assessment_date].get(item.activity_id)
        if current is None or item.id > current.id:
            by_date[item.assessment_date][item.activity_id] = item

    def aggregate(items: list[tuple[Decimal, Decimal | None]]) -> Decimal | None:
        if not items:
            return None
        weighted = [(value, weight) for value, weight in items if weight and weight > 0]
        total_weight = sum((weight for _, weight in weighted), Decimal("0"))
        if total_weight > 0:
            return _decimal(
                sum((value * weight for value, weight in weighted), Decimal("0"))
                / total_weight
            )
        return _decimal(
            sum((value for value, _ in items), Decimal("0")) / Decimal(len(items))
        )

    points = []
    for item_date, by_activity in sorted(by_date.items()):
        planned = aggregate(
            [
                (item.planned_progress, weights.get(item.activity_id))
                for item in by_activity.values()
                if item.planned_progress is not None
            ]
        )
        actual = aggregate(
            [
                (item.fused_progress, weights.get(item.activity_id))
                for item in by_activity.values()
                if item.fused_progress is not None
            ]
        )
        if planned is not None and actual is not None:
            points.append(
                {
                    "date": item_date,
                    "planned_progress": planned,
                    "actual_progress": actual,
                }
            )
    return points


def _weighted_activity_data(
    db: Session, project_id: int
) -> tuple[list[Activity], dict[int, Decimal | None]]:
    activities = list(
        db.scalars(
            select(Activity)
            .options(selectinload(Activity.schedule_activity))
            .where(Activity.project_id == project_id)
        ).all()
    )
    return activities, {
        activity.id: (
            activity.schedule_activity.weightage
            if activity.schedule_activity is not None
            else None
        )
        for activity in activities
    }


@router.get(
    "/api/projects/{project_id}/dashboard/summary",
    response_model=ProjectDashboardSummary,
)
def get_project_dashboard_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDashboardSummary:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if current_user.role not in ALLOWED_ROLES or not _can_view_project(
        db, project_id, current_user
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You are not authorized to view this project dashboard",
        )

    activities = list(
        db.scalars(
            select(Activity)
            .options(selectinload(Activity.schedule_activity))
            .where(Activity.project_id == project_id)
            .order_by(Activity.id)
        ).all()
    )
    activity_ids = [activity.id for activity in activities]
    assessments = (
        list(
            db.scalars(
                select(ProgressAssessment)
                .where(ProgressAssessment.project_id == project_id)
                .order_by(ProgressAssessment.assessment_date.desc(), ProgressAssessment.id.desc())
            ).all()
        )
        if activity_ids
        else []
    )
    latest_assessments = _latest_by_activity(assessments)

    weights = {
        activity.id: (
            activity.schedule_activity.weightage
            if activity.schedule_activity is not None
            else None
        )
        for activity in activities
    }
    weighted_planned = [
        (item.planned_progress, weights[item.activity_id])
        for item in latest_assessments.values()
        if item.planned_progress is not None and weights[item.activity_id] is not None
    ]
    weighted_actual = [
        (item.fused_progress, weights[item.activity_id])
        for item in latest_assessments.values()
        if item.fused_progress is not None and weights[item.activity_id] is not None
    ]

    def aggregate(values: list[tuple[Decimal, Decimal | None]]) -> Decimal | None:
        if not values:
            return None
        weight_total = sum((weight for _, weight in values if weight and weight > 0), Decimal("0"))
        if weight_total > 0:
            return _decimal(
                sum((value * weight for value, weight in values if weight), Decimal("0"))
                / weight_total
            )
        return _decimal(
            sum((value for value, _ in values), Decimal("0")) / Decimal(len(values))
        )

    def fallback(field: str) -> Decimal | None:
        values = [
            getattr(item, field)
            for item in latest_assessments.values()
            if getattr(item, field) is not None
        ]
        return _decimal(sum(values, Decimal("0")) / Decimal(len(values))) if values else None

    planned = aggregate(weighted_planned) or fallback("planned_progress")
    actual = aggregate(weighted_actual) or fallback("fused_progress")
    variance = _decimal(actual - planned) if actual is not None and planned is not None else None

    status_counts = Counter(activity.status for activity in activities)
    delayed = [
        {
            "activity_id": activity.id,
            "activity_name": activity.name,
            "planned_progress": latest_assessments[activity.id].planned_progress,
            "fused_progress": latest_assessments[activity.id].fused_progress,
            "variance": latest_assessments[activity.id].variance_from_plan,
            "predicted_delay_days": None,
        }
        for activity in activities
        if activity.id in latest_assessments
        and latest_assessments[activity.id].variance_from_plan is not None
        and latest_assessments[activity.id].variance_from_plan < 0
    ]

    prediction_rows = list(
        db.execute(
            select(ActivityRiskPrediction, Activity.name)
            .join(Activity, Activity.id == ActivityRiskPrediction.activity_id)
            .where(ActivityRiskPrediction.project_id == project_id)
            .order_by(ActivityRiskPrediction.prediction_date.desc(), ActivityRiskPrediction.id.desc())
        ).all()
    )
    latest_predictions: dict[int, tuple[ActivityRiskPrediction, str]] = {}
    for prediction, name in prediction_rows:
        latest_predictions.setdefault(prediction.activity_id, (prediction, name))
    for item in delayed:
        latest = latest_predictions.get(item["activity_id"])
        if latest is not None:
            item["predicted_delay_days"] = latest[0].predicted_delay_days
    risk_counts = Counter(prediction.risk_level for prediction, _ in latest_predictions.values())
    high_risk = [
        {
            "activity_id": prediction.activity_id,
            "activity_name": name,
            "risk_level": prediction.risk_level,
            "risk_score": prediction.risk_score,
            "primary_risk": prediction.primary_risk,
            "predicted_delay_days": prediction.predicted_delay_days,
        }
        for prediction, name in sorted(
            latest_predictions.values(), key=lambda item: item[0].risk_score, reverse=True
        )
        if prediction.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    ][:TOP_LIMIT]

    evidence_counts = Counter(
        db.scalars(
            select(Evidence.status).where(Evidence.project_id == project_id)
        ).all()
    )
    recovery_counts = Counter(
        db.scalars(
            select(RecoveryRecommendation.status).where(
                RecoveryRecommendation.project_id == project_id
            )
        ).all()
    )
    active_recommendations = list(
        db.scalars(
            select(RecoveryRecommendation)
            .where(
                RecoveryRecommendation.project_id == project_id,
                RecoveryRecommendation.status.in_(
                    [RecommendationStatus.SUGGESTED, RecommendationStatus.ACCEPTED]
                ),
            )
            .order_by(RecoveryRecommendation.created_at.desc())
            .limit(TOP_LIMIT)
        ).all()
    )

    evidence_verified = evidence_counts[EvidenceStatus.VERIFIED]
    evidence_rejected = evidence_counts[EvidenceStatus.REJECTED]
    evidence_pending = evidence_counts[EvidenceStatus.VERIFICATION_PENDING]
    return {
        "project": {"id": project.id, "name": project.name, "status": project.status},
        "progress": {"planned": planned, "actual": actual, "variance": variance},
        "activities": {
            "total": len(activities),
            "completed": status_counts[FieldActivityStatus.COMPLETED],
            "in_progress": status_counts[FieldActivityStatus.IN_PROGRESS],
            "not_started": status_counts[FieldActivityStatus.NOT_STARTED],
            "submitted": status_counts[FieldActivityStatus.SUBMITTED],
        },
        "delay": {
            "delayed_count": len(delayed),
            "top_delayed_activities": sorted(
                delayed, key=lambda item: item["variance"]
            )[:TOP_LIMIT],
        },
        "risk": {
            "low": risk_counts[RiskLevel.LOW],
            "medium": risk_counts[RiskLevel.MEDIUM],
            "high": risk_counts[RiskLevel.HIGH],
            "critical": risk_counts[RiskLevel.CRITICAL],
            "top_risk_activities": high_risk,
        },
        "evidence": {
            "total": sum(evidence_counts.values()),
            "pending_verification": evidence_pending,
            "verified": evidence_verified,
            "rejected": evidence_rejected,
        },
        "recovery": {
            "suggested": recovery_counts[RecommendationStatus.SUGGESTED],
            "accepted": recovery_counts[RecommendationStatus.ACCEPTED],
            "implemented": recovery_counts[RecommendationStatus.IMPLEMENTED],
            "active_recommendations": [
                {
                    "id": item.id,
                    "activity_id": item.activity_id,
                    "type": item.recommendation_type,
                    "priority": item.priority,
                    "title": item.title,
                    "status": item.status,
                }
                for item in active_recommendations
            ],
        },
    }


@router.get(
                "/api/projects/{project_id}/dashboard/progress-timeline",
                response_model=ProgressTimelineResponse,
)
def get_progress_timeline(
                project_id: int,
                start_date: date | None = None,
                end_date: date | None = None,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user),
) -> dict:
                _dashboard_project(db, project_id, current_user)
                _, weights = _weighted_activity_data(db, project_id)
                assessments = list(
                    db.scalars(
                        select(ProgressAssessment)
                        .where(ProgressAssessment.project_id == project_id)
                        .order_by(ProgressAssessment.assessment_date, ProgressAssessment.id)
                    ).all()
                )
                points = _progress_points(assessments, weights)
                selected_start, selected_end = _date_range(
                    start_date, end_date, [item["date"] for item in points]
                )
                if selected_start is not None:
                    points = [
                        item
                        for item in points
                        if (selected_start is None or item["date"] >= selected_start)
                        and (selected_end is None or item["date"] <= selected_end)
                    ]
                return {"project_id": project_id, "data": points}


@router.get(
                "/api/projects/{project_id}/dashboard/progress-trend",
                response_model=ProgressTrendResponse,
)
def get_progress_trend(
                project_id: int,
                start_date: date | None = None,
                end_date: date | None = None,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user),
) -> dict:
                _dashboard_project(db, project_id, current_user)
                _, weights = _weighted_activity_data(db, project_id)
                assessments = list(
                    db.scalars(
                        select(ProgressAssessment)
                        .where(ProgressAssessment.project_id == project_id)
                        .order_by(ProgressAssessment.assessment_date, ProgressAssessment.id)
                    ).all()
                )
                history = _progress_points(assessments, weights)
                selected_start, selected_end = _date_range(
                    start_date, end_date, [item["date"] for item in history]
                )
                if selected_start is not None:
                    history = [
                        item
                        for item in history
                        if item["date"] >= selected_start
                        and (selected_end is None or item["date"] <= selected_end)
                    ]
                current = history[-1] if history else {
                    "planned_progress": None,
                    "actual_progress": None,
                }
                planned = current.get("planned_progress")
                actual = current.get("actual_progress")
                change = None
                direction = "INSUFFICIENT_DATA"
                if len(history) >= 2:
                    change = _decimal(history[-1]["actual_progress"] - history[-2]["actual_progress"])
                    if change > 0:
                        direction = "IMPROVING"
                    elif change < 0:
                        direction = "DECLINING"
                    else:
                        direction = "STABLE"
                return {
                    "current": {
                        "planned": planned,
                        "actual": actual,
                        "variance": _decimal(actual - planned)
                        if actual is not None and planned is not None
                        else None,
                    },
                    "trend": {"direction": direction, "change": change},
                    "history": history,
                }


def _prediction_rows(
                db: Session, project_id: int
) -> list[tuple[ActivityRiskPrediction, str]]:
                return list(
                    db.execute(
                        select(ActivityRiskPrediction, Activity.name)
                        .join(Activity, Activity.id == ActivityRiskPrediction.activity_id)
                        .where(ActivityRiskPrediction.project_id == project_id)
                        .order_by(
                            ActivityRiskPrediction.prediction_date,
                            ActivityRiskPrediction.id,
                        )
                    ).all()
                )


def _latest_predictions_as_of(
                rows: list[tuple[ActivityRiskPrediction, str]],
                item_date: date,
) -> dict[int, tuple[ActivityRiskPrediction, str]]:
                latest: dict[int, tuple[ActivityRiskPrediction, str]] = {}
                for prediction, name in rows:
                    if prediction.prediction_date <= item_date:
                        latest[prediction.activity_id] = (prediction, name)
                return latest


@router.get(
                "/api/projects/{project_id}/dashboard/risk-timeline",
                response_model=RiskTimelineResponse,
)
def get_risk_timeline(
                project_id: int,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user),
) -> dict:
                _dashboard_project(db, project_id, current_user)
                rows = _prediction_rows(db, project_id)
                dates = sorted({prediction.prediction_date for prediction, _ in rows})
                data = []
                for item_date in dates:
                    latest = _latest_predictions_as_of(rows, item_date)
                    counts = Counter(prediction.risk_level for prediction, _ in latest.values())
                    data.append(
                        {
                            "date": item_date,
                            "low": counts[RiskLevel.LOW],
                            "medium": counts[RiskLevel.MEDIUM],
                            "high": counts[RiskLevel.HIGH],
                            "critical": counts[RiskLevel.CRITICAL],
                        }
                    )
                return {"project_id": project_id, "data": data}


@router.get(
                "/api/projects/{project_id}/dashboard/delay-summary",
                response_model=DelaySummaryResponse,
)
def get_delay_summary(
                project_id: int,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user),
) -> dict:
                _dashboard_project(db, project_id, current_user)
                rows = _prediction_rows(db, project_id)
                latest = _latest_predictions_as_of(
                    rows,
                    max((prediction.prediction_date for prediction, _ in rows), default=date.min),
                )
                delayed = [
                    (prediction, name)
                    for prediction, name in latest.values()
                    if prediction.predicted_delay_days is not None
                    and prediction.predicted_delay_days > 0
                ]
                highest = max(delayed, key=lambda item: item[0].predicted_delay_days) if delayed else None
                highest_payload = None
                if highest is not None:
                    prediction, name = highest
                    highest_payload = {
                        "activity_id": prediction.activity_id,
                        "activity_name": name,
                        "predicted_delay_days": prediction.predicted_delay_days,
                    }
                return {
                    "total_delayed_activities": len(delayed),
                    "total_predicted_delay_days": _decimal(
                        sum((prediction.predicted_delay_days for prediction, _ in delayed), Decimal("0"))
                    ) or Decimal("0"),
                    "highest_delay_activity": highest_payload,
                }


@router.get(
                "/api/projects/{project_id}/dashboard/recovery-summary",
                response_model=RecoverySummaryResponse,
)
def get_recovery_summary(
                project_id: int,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user),
) -> dict:
                _dashboard_project(db, project_id, current_user)
                rows = list(
                    db.scalars(
                        select(RecoveryRecommendation)
                        .where(RecoveryRecommendation.project_id == project_id)
                        .order_by(RecoveryRecommendation.created_at.desc())
                    ).all()
                )
                counts = Counter(item.status for item in rows)
                return {
                    "suggested": counts[RecommendationStatus.SUGGESTED],
                    "accepted": counts[RecommendationStatus.ACCEPTED],
                    "implemented": counts[RecommendationStatus.IMPLEMENTED],
                    "rejected": counts[RecommendationStatus.REJECTED],
                    "top_recommendations": [
                        {
                            "activity_id": item.activity_id,
                            "type": item.recommendation_type,
                            "priority": item.priority,
                            "status": item.status,
                        }
                        for item in rows[:TOP_LIMIT]
                    ],
                }


@router.get(
                "/api/projects/{project_id}/dashboard/timeline",
                response_model=CombinedTimelineResponse,
)
def get_combined_timeline(
                project_id: int,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user),
) -> dict:
                _dashboard_project(db, project_id, current_user)
                _, weights = _weighted_activity_data(db, project_id)
                assessments = list(
                    db.scalars(
                        select(ProgressAssessment)
                        .where(ProgressAssessment.project_id == project_id)
                        .order_by(ProgressAssessment.assessment_date, ProgressAssessment.id)
                    ).all()
                )
                progress = {
                    item["date"]: item
                    for item in _progress_points(assessments, weights)
                }
                prediction_rows = _prediction_rows(db, project_id)
                dates = sorted(
                    set(progress) | {prediction.prediction_date for prediction, _ in prediction_rows}
                )
                events = []
                for item_date in dates:
                    latest = _latest_predictions_as_of(prediction_rows, item_date)
                    counts = Counter(prediction.risk_level for prediction, _ in latest.values())
                    delays = [
                        prediction.predicted_delay_days
                        for prediction, _ in latest.values()
                        if prediction.predicted_delay_days is not None
                    ]
                    progress_item = progress.get(item_date)
                    events.append(
                        {
                            "date": item_date,
                            "planned_progress": progress_item["planned_progress"]
                            if progress_item
                            else None,
                            "actual_progress": progress_item["actual_progress"]
                            if progress_item
                            else None,
                            "variance": _decimal(
                                progress_item["actual_progress"] - progress_item["planned_progress"]
                            )
                            if progress_item
                            else None,
                            "high_risk_activities": counts[RiskLevel.HIGH],
                            "critical_risk_activities": counts[RiskLevel.CRITICAL],
                            "predicted_delay_days": _decimal(sum(delays, Decimal("0"))) or Decimal("0"),
                        }
                    )
                return {"project_id": project_id, "events": events}
