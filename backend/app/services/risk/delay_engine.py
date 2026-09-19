from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity_measured_progress import (
    ActivityMeasuredProgress,
    MeasuredProgressVerificationStatus,
)
from app.models.field_activity import Activity
from app.models.progress_assessment import ProgressAssessment

ONE_PLACE = Decimal("0.1")


@dataclass(frozen=True)
class DelayEstimate:
    predicted_delay_days: Decimal | None
    expected_completion_date: date | None
    source_assessment_ids: list[int]
    source_observation_ids: list[int]
    confidence_score: Decimal
    confidence_level: str
    explanation: str


def _round_days(value: Decimal) -> Decimal:
    return value.quantize(ONE_PLACE, rounding=ROUND_HALF_UP)


def _verified_observations(
    db: Session, activity_id: int, assessment_date: date
) -> list[tuple[ProgressAssessment, ActivityMeasuredProgress]]:
    return list(
        db.execute(
            select(ProgressAssessment, ActivityMeasuredProgress)
            .join(
                ActivityMeasuredProgress,
                (ActivityMeasuredProgress.activity_id == ProgressAssessment.activity_id)
                & (
                    ActivityMeasuredProgress.assessment_date
                    == ProgressAssessment.assessment_date
                ),
            )
            .where(
                ProgressAssessment.activity_id == activity_id,
                ProgressAssessment.assessment_date <= assessment_date,
                ProgressAssessment.fused_progress.is_not(None),
                ProgressAssessment.measured_progress.is_not(None),
                ActivityMeasuredProgress.verification_status
                == MeasuredProgressVerificationStatus.VERIFIED,
            )
            .order_by(
                ProgressAssessment.assessment_date.desc(),
                ProgressAssessment.id.desc(),
            )
            .limit(10)
        ).all()
    )


def _confidence(
    history_count: int,
    has_fused_progress: bool,
    has_schedule: bool,
    stable_trend: bool,
) -> tuple[Decimal, str]:
    if not has_fused_progress or not has_schedule:
        return Decimal("30"), "LOW"
    if history_count < 2:
        return Decimal("55"), "LOW"
    if not stable_trend:
        return Decimal("65"), "MEDIUM"
    return Decimal("85"), "HIGH"


def predict_activity_delay(
    db: Session,
    activity: Activity,
    assessment_date: date,
) -> DelayEstimate:
    schedule = activity.schedule_activity
    observations = _verified_observations(db, activity.id, assessment_date)
    assessments = [assessment for assessment, _ in observations]
    source_assessment_ids = [item.id for item in assessments[:2]]
    source_observation_ids = [item.id for _, item in observations[:2]]
    latest = assessments[0] if assessments else None
    fused_progress = latest.fused_progress if latest else None
    planned_progress = (
        latest.planned_progress
        if latest and latest.planned_progress is not None
        else schedule.planned_progress if schedule else None
    )
    has_schedule = (
        schedule is not None
        and schedule.planned_start is not None
        and schedule.planned_finish is not None
    )

    rate: Decimal | None = None
    stable_trend = False
    if len(assessments) >= 2:
        latest_history, previous_history = assessments[:2]
        elapsed_days = (
            latest_history.assessment_date - previous_history.assessment_date
        ).days
        if elapsed_days > 0:
            progress_gain = latest_history.fused_progress - previous_history.fused_progress
            rate = progress_gain / Decimal(elapsed_days)
            if len(assessments) >= 3:
                older_history = assessments[2]
                older_elapsed_days = (
                    previous_history.assessment_date - older_history.assessment_date
                ).days
                older_gain = previous_history.fused_progress - older_history.fused_progress
                stable_trend = (
                    older_elapsed_days > 0
                    and older_gain >= 0
                    and progress_gain >= 0
                )

    confidence, confidence_level = _confidence(
        len(assessments),
        fused_progress is not None,
        has_schedule,
        stable_trend,
    )

    def unavailable(message: str) -> DelayEstimate:
        return DelayEstimate(
            None,
            None,
            source_assessment_ids,
            source_observation_ids,
            confidence,
            "LOW",
            message,
        )

    if fused_progress is None or planned_progress is None:
        return unavailable(
            "Delay unavailable - verified measured progress is not available."
        )
    if not has_schedule:
        return unavailable("Delay unavailable - schedule dates are unavailable.")
    if rate is None or rate <= 0:
        return unavailable(
            "Delay unavailable - at least two independent verified measured "
            "observations with a positive productivity rate are required."
        )

    remaining_work = max(Decimal("0"), Decimal("100") - fused_progress)
    estimated_days_to_finish = remaining_work / rate
    completion_days = estimated_days_to_finish.to_integral_value(rounding=ROUND_CEILING)
    expected_completion_date = assessment_date + timedelta(
        days=max(0, int(completion_days))
    )
    planned_remaining_days = Decimal(
        max(0, (schedule.planned_finish - assessment_date).days)
    )
    delay_days = _round_days(
        max(Decimal("0"), estimated_days_to_finish - planned_remaining_days)
    )
    progress_gap = planned_progress - fused_progress
    explanation = (
        f"Activity is {progress_gap}% behind planned progress and the verified "
        f"productivity rate indicates an estimated {delay_days} day delay."
    )
    return DelayEstimate(
        delay_days,
        expected_completion_date,
        source_assessment_ids,
        source_observation_ids,
        confidence,
        confidence_level,
        explanation,
    )
