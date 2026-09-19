from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence_comparison_analysis import EvidenceComparisonAnalysis
from app.models.evidence import Evidence
from app.models.field_activity import Activity
from app.models.planning import PlannedProgress
from app.models.progress_assessment import ProgressAssessment
from app.models.activity_measured_progress import (
    ActivityMeasuredProgress,
    MeasuredProgressVerificationStatus,
)
from app.services.progress.fusion_service import (
    calculate_fused_progress,
    determine_assessment_status,
)

def calculate_measured_progress(
    completed_quantity: Decimal, planned_quantity: Decimal
) -> Decimal:
    if planned_quantity <= 0:
        raise ValueError("planned_quantity must be greater than zero")
    if completed_quantity < 0 or completed_quantity > planned_quantity:
        raise ValueError("completed_quantity must be between zero and planned_quantity")
    return (completed_quantity / planned_quantity * Decimal("100")).quantize(
        Decimal("0.01")
    )


def _evidence_for_date(
    db: Session, activity_id: int, assessment_date: date
) -> Evidence | None:
    candidates = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.activity_id == activity_id)
            .order_by(Evidence.uploaded_at.desc(), Evidence.id.desc())
        ).all()
    )
    for evidence in candidates:
        evidence_date = (
            evidence.captured_at.date()
            if evidence.captured_at is not None
            else evidence.uploaded_at.date()
        )
        if evidence_date == assessment_date:
            return evidence
    return None


def assess_activity_progress(
    db: Session,
    activity: Activity,
    assessment_date: date,
) -> ProgressAssessment:
    planned = db.scalar(
        select(PlannedProgress)
        .where(
            PlannedProgress.schedule_activity_id == activity.schedule_activity_id,
            PlannedProgress.date == assessment_date,
        )
        .order_by(PlannedProgress.id.desc())
    )
    evidence = _evidence_for_date(db, activity.id, assessment_date)
    comparison = None
    if evidence is not None:
        comparison = db.scalar(
            select(EvidenceComparisonAnalysis)
            .where(
                EvidenceComparisonAnalysis.activity_id == activity.id,
                EvidenceComparisonAnalysis.current_evidence_id == evidence.id,
                EvidenceComparisonAnalysis.comparison_status == "COMPLETED",
            )
            .order_by(
                EvidenceComparisonAnalysis.created_at.desc(),
                EvidenceComparisonAnalysis.id.desc(),
            )
        )

    planned_progress = planned.planned_percentage if planned else None
    measured = db.scalar(
        select(ActivityMeasuredProgress)
        .where(
            ActivityMeasuredProgress.activity_id == activity.id,
            ActivityMeasuredProgress.assessment_date == assessment_date,
            ActivityMeasuredProgress.verification_status
            == MeasuredProgressVerificationStatus.VERIFIED,
        )
    )
    measured_progress = None
    if measured is not None and measured.planned_quantity > 0:
        measured_progress = calculate_measured_progress(
            measured.completed_quantity, measured.planned_quantity
        )
    reported_progress = evidence.reported_progress if evidence else None
    ai_estimated_progress = (
        comparison.absolute_progress_estimate if comparison else None
    )
    ai_confidence = (
        comparison.absolute_progress_confidence
        if comparison and comparison.absolute_progress_confidence is not None
        else None
    )
    fused_progress = measured_progress
    variance_from_plan = None
    variance_from_reported = None
    if measured_progress is None and (
        planned_progress is not None
        and reported_progress is not None
        and ai_estimated_progress is not None
        and ai_confidence is not None
    ):
        fused_progress = calculate_fused_progress(
            reported_progress, ai_estimated_progress, ai_confidence
        )
        variance_from_plan = (fused_progress - planned_progress).quantize(Decimal("0.01"))
        variance_from_reported = (
            fused_progress - reported_progress
        ).quantize(Decimal("0.01"))

    assessment = db.scalar(
        select(ProgressAssessment)
        .where(
            ProgressAssessment.activity_id == activity.id,
            ProgressAssessment.assessment_date == assessment_date,
        )
        .order_by(
            ProgressAssessment.comparison_id.is_not(None).desc(),
            ProgressAssessment.id.desc(),
        )
    )
    if assessment is None:
        assessment = ProgressAssessment(
            project_id=activity.project_id,
            activity_id=activity.id,
            schedule_activity_id=activity.schedule_activity_id,
            assessment_date=assessment_date,
        )
        db.add(assessment)
    assessment.evidence_id = evidence.id if evidence else None
    assessment.comparison_id = comparison.id if comparison else None
    assessment.planned_progress = planned_progress
    assessment.reported_progress = reported_progress
    assessment.measured_progress = measured_progress
    assessment.ai_estimated_progress = ai_estimated_progress
    assessment.ai_confidence = ai_confidence
    assessment.fused_progress = fused_progress
    assessment.variance_from_plan = variance_from_plan
    assessment.variance_from_reported = variance_from_reported
    assessment.assessment_status = determine_assessment_status(variance_from_plan)
    assessment.assessed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)
    return assessment
