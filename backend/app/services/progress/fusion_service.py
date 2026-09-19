from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings
from app.models.progress_assessment import ProgressAssessmentStatus


TWO_PLACES = Decimal("0.01")


def calculate_fused_progress(
    reported_progress: Decimal,
    ai_estimated_progress: Decimal,
    ai_confidence: Decimal,
) -> Decimal:
    if ai_confidence >= settings.fusion_high_confidence_threshold:
        reported_weight = settings.fusion_high_reported_weight
        ai_weight = settings.fusion_high_ai_weight
    elif ai_confidence >= settings.fusion_medium_confidence_threshold:
        reported_weight = settings.fusion_medium_reported_weight
        ai_weight = settings.fusion_medium_ai_weight
    else:
        reported_weight = Decimal("1")
        ai_weight = Decimal("0")
    return (reported_progress * reported_weight + ai_estimated_progress * ai_weight).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )


def determine_assessment_status(
    variance_from_plan: Decimal | None,
) -> ProgressAssessmentStatus:
    if variance_from_plan is None:
        return ProgressAssessmentStatus.INSUFFICIENT_EVIDENCE
    if variance_from_plan >= settings.minor_variance_threshold:
        return ProgressAssessmentStatus.ON_TRACK
    if variance_from_plan >= settings.significant_variance_threshold:
        return ProgressAssessmentStatus.MINOR_VARIANCE
    return ProgressAssessmentStatus.SIGNIFICANT_VARIANCE
