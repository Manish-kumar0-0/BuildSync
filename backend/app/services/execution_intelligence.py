from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.field_activity import Activity
from app.models.activity_measured_progress import (
    ActivityMeasuredProgress,
    MeasuredProgressVerificationStatus,
)
from app.models.planning import PlannedProgress
from app.models.progress_assessment import ProgressAssessment
from app.models.recovery import RecoveryRecommendation
from app.models.risk_prediction import ActivityRiskPrediction
from app.services.risk.delay_engine import predict_activity_delay


def _planned_progress(
    db: Session, activity: Activity, assessment_date: date
) -> Decimal | None:
    point = db.scalar(
        select(PlannedProgress)
        .where(
            PlannedProgress.schedule_activity_id == activity.schedule_activity_id,
            PlannedProgress.date <= assessment_date,
        )
        .order_by(PlannedProgress.date.desc(), PlannedProgress.id.desc())
    )
    if point is not None:
        return point.planned_percentage
    schedule = activity.schedule_activity
    return schedule.planned_progress if schedule and schedule.planned_start <= assessment_date else None


def _assessments(
    db: Session, activity_id: int, assessment_date: date
) -> list[ProgressAssessment]:
    return list(
        db.scalars(
            select(ProgressAssessment)
            .where(
                ProgressAssessment.activity_id == activity_id,
                ProgressAssessment.assessment_date <= assessment_date,
                ProgressAssessment.fused_progress.is_not(None),
                ProgressAssessment.measured_progress.is_not(None),
            )
            .order_by(
                ProgressAssessment.assessment_date.desc(),
                ProgressAssessment.id.desc(),
            )
        ).all()
    )


def build_execution_intelligence(
    db: Session, activity: Activity, assessment_date: date
) -> dict:
    assessment = db.scalar(
        select(ProgressAssessment)
        .where(
            ProgressAssessment.activity_id == activity.id,
            ProgressAssessment.assessment_date <= assessment_date,
        )
        .order_by(
            ProgressAssessment.assessment_date.desc(),
            ProgressAssessment.id.desc(),
        )
    )
    planned = _planned_progress(db, activity, assessment_date)
    actual = assessment.fused_progress if assessment else None
    actual_progress_source = "UNAVAILABLE"
    actual_progress_confidence = None
    if assessment and assessment.fused_progress is not None:
        if assessment.measured_progress is not None:
            actual_progress_source = "MEASURED_VERIFIED"
            actual_progress_confidence = Decimal("100")
        elif assessment.ai_estimated_progress is not None:
            actual_progress_source = "GEMINI"
            actual_progress_confidence = assessment.ai_confidence
        elif assessment.reported_progress is not None:
            actual_progress_source = "REPORTED"
    actual_progress_reason = (
        "Validated fused progress is available."
        if actual is not None
        else (
            "Measured completion quantity unavailable for this activity; "
            "Gemini did not provide a validated absolute-progress estimate."
        )
    )
    variance = (
        (actual - planned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if actual is not None and planned is not None
        else None
    )
    if variance is None:
        variance_status = "UNAVAILABLE"
    elif variance > 0:
        variance_status = "AHEAD"
    elif variance < 0:
        variance_status = "BEHIND"
    else:
        variance_status = "ON_PLAN"

    history = _assessments(db, activity.id, assessment_date)
    productivity_rate = None
    observation_ids: list[int] = []
    observation_progress_ids: list[int] = []
    if len(history) >= 2:
        latest, previous = history[0], history[1]
        elapsed_days = (latest.assessment_date - previous.assessment_date).days
        if elapsed_days > 0:
            productivity_rate = (
                (latest.fused_progress - previous.fused_progress)
                / Decimal(elapsed_days)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            observation_ids = [latest.id, previous.id]
            observation_progress_ids = [
                item.id
                for item in db.scalars(
                    select(ActivityMeasuredProgress)
                    .where(
                        ActivityMeasuredProgress.activity_id == activity.id,
                        ActivityMeasuredProgress.assessment_date.in_(
                            [latest.assessment_date, previous.assessment_date]
                        ),
                        ActivityMeasuredProgress.verification_status
                        == MeasuredProgressVerificationStatus.VERIFIED,
                    )
                    .order_by(ActivityMeasuredProgress.assessment_date.desc())
                ).all()
            ]
    productivity_status = "AVAILABLE" if productivity_rate is not None else "INSUFFICIENT_HISTORY"
    productivity_reason = (
        "Calculated from the two latest independent dated fused-progress assessments."
        if productivity_rate is not None
        else "At least two independent dated actual/fused-progress observations are required."
    )

    delay = predict_activity_delay(db, activity, assessment_date)
    delay_status = (
        "AVAILABLE"
        if delay.predicted_delay_days is not None
        else "INSUFFICIENT_PRODUCTIVITY_HISTORY"
    )
    risk = db.scalar(
        select(ActivityRiskPrediction)
        .where(
            ActivityRiskPrediction.activity_id == activity.id,
        )
        .order_by(
            ActivityRiskPrediction.comparison_id.is_not(None).desc(),
            ActivityRiskPrediction.prediction_date.desc(),
            ActivityRiskPrediction.id.desc(),
        )
    )
    recommendation = db.scalar(
        select(RecoveryRecommendation)
        .where(
            RecoveryRecommendation.activity_id == activity.id,
            RecoveryRecommendation.risk_prediction_id == risk.id if risk else False,
        )
        .order_by(RecoveryRecommendation.id.desc())
    )
    schedule = activity.schedule_activity
    return {
        "activity_id": activity.id,
        "assessment_date": assessment_date,
        "planned_start": schedule.planned_start if schedule else None,
        "planned_end": schedule.planned_finish if schedule else None,
        "planned_progress": planned,
        "actual_progress": actual,
        "actual_progress_source": actual_progress_source,
        "actual_progress_confidence": actual_progress_confidence,
        "actual_progress_reason": actual_progress_reason,
        "variance": variance,
        "variance_status": variance_status,
        "assessment_id": assessment.id if assessment else None,
        "productivity_rate": productivity_rate,
        "productivity_observation_ids": observation_ids,
        "productivity_source_assessment_ids": observation_ids,
        "productivity_source_observation_ids": observation_progress_ids,
        "productivity_status": productivity_status,
        "productivity_reason": productivity_reason,
        "predicted_delay_days": delay.predicted_delay_days,
        "expected_completion_date": delay.expected_completion_date,
        "delay_status": delay_status,
        "delay_reason": delay.explanation,
        "delay_source_assessment_id": assessment.id if delay.predicted_delay_days is not None and assessment else None,
        "delay_source_assessment_ids": delay.source_assessment_ids,
        "delay_source_observation_ids": delay.source_observation_ids,
        "risk_prediction_id": risk.id if risk else None,
        "recovery_recommendation_id": recommendation.id if recommendation else None,
    }
