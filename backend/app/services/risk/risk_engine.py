from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_analysis import AIAnalysis, AIAnalysisStatus
from app.models.evidence import Evidence
from app.models.evidence_comparison_analysis import EvidenceComparisonAnalysis
from app.models.field_activity import Activity, FieldActivityStatus
from app.models.progress_assessment import ProgressAssessment
from app.models.risk_prediction import (
    ActivityRiskPrediction,
    PrimaryRisk,
    RiskLevel,
    RiskPredictionStatus,
)
from app.services.risk.delay_engine import predict_activity_delay

TWO_PLACES = Decimal("0.01")
RECENT_EVIDENCE_DAYS = 7


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _progress_lag_impact(lag: Decimal | None) -> int:
    if lag is None or lag <= 0:
        return 0
    if lag <= 5:
        return 10
    if lag <= 10:
        return 30
    if lag <= 20:
        return 60
    return 85


def _deadline_impact(activity: Activity, assessment_date: date) -> tuple[int, int | None]:
    schedule = activity.schedule_activity
    if schedule is None or schedule.planned_finish is None:
        return 0, None
    if activity.status == FieldActivityStatus.COMPLETED:
        return 0, (schedule.planned_finish - assessment_date).days
    days_remaining = (schedule.planned_finish - assessment_date).days
    if days_remaining > 14:
        return 0, days_remaining
    if days_remaining >= 7:
        return 20, days_remaining
    if days_remaining >= 3:
        return 45, days_remaining
    if days_remaining >= 1:
        return 70, days_remaining
    return 90, days_remaining


def _evidence_for_activity(
    db: Session, activity_id: int
) -> list[Evidence]:
    return list(
        db.scalars(
            select(Evidence)
            .where(Evidence.activity_id == activity_id)
            .order_by(Evidence.uploaded_at.desc(), Evidence.id.desc())
        ).all()
    )


def _latest_completed_analysis(
    db: Session, evidence: list[Evidence], assessment_date: date
) -> AIAnalysis | None:
    evidence_ids = [item.id for item in evidence]
    if not evidence_ids:
        return None
    return db.scalar(
        select(AIAnalysis)
        .join(Evidence, Evidence.id == AIAnalysis.evidence_id)
        .where(
            AIAnalysis.evidence_id.in_(evidence_ids),
            AIAnalysis.analysis_status == AIAnalysisStatus.COMPLETED,
            AIAnalysis.created_at < assessment_date + timedelta(days=1),
        )
        .order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc())
    )


def _trend(
    assessments: list[ProgressAssessment],
) -> tuple[str, int]:
    values = [
        item.fused_progress
        for item in assessments
        if item.fused_progress is not None
    ]
    if len(values) < 2:
        return "INSUFFICIENT_DATA", 20
    latest, previous = values[0], values[1]
    if latest > previous:
        return "IMPROVING", 0
    if latest < previous:
        return "DECLINING", 45
    return "STABLE", 10


def _risk_level(score: Decimal) -> RiskLevel:
    if score <= settings.risk_low_max_score:
        return RiskLevel.LOW
    if score <= settings.risk_medium_max_score:
        return RiskLevel.MEDIUM
    if score <= settings.risk_high_max_score:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _primary_risk(factors: list[dict[str, Any]]) -> PrimaryRisk:
    factor_map = {
        "progress_lag": PrimaryRisk.PROGRESS_LAG,
        "deadline": PrimaryRisk.MISSED_MILESTONE,
        "evidence_gap": PrimaryRisk.INSUFFICIENT_EVIDENCE,
        "ai_confidence": PrimaryRisk.LOW_AI_CONFIDENCE,
        "activity_status": PrimaryRisk.NOT_STARTED,
        "progress_trend": PrimaryRisk.DECLINING_PROGRESS,
    }
    highest = max(factors, key=lambda factor: (factor["impact"], -factor["order"]))
    if highest["impact"] <= 0:
        return PrimaryRisk.UNKNOWN
    return factor_map.get(highest["factor"], PrimaryRisk.UNKNOWN)


def calculate_activity_risk(
    db: Session,
    activity: Activity,
    assessment_date: date,
) -> ActivityRiskPrediction:
    schedule = activity.schedule_activity
    evidence = _evidence_for_activity(db, activity.id)
    recent_cutoff = assessment_date - timedelta(days=RECENT_EVIDENCE_DAYS)
    recent_evidence = [
        item
        for item in evidence
        if (
            item.captured_at.date()
            if item.captured_at is not None
            else item.uploaded_at.date()
        )
        >= recent_cutoff
        and (
            item.captured_at.date()
            if item.captured_at is not None
            else item.uploaded_at.date()
        )
        <= assessment_date
    ]
    evidence_impact = 0 if recent_evidence else (60 if not evidence else 40)
    latest_analysis = _latest_completed_analysis(db, evidence, assessment_date)
    latest_comparison = db.scalar(
        select(EvidenceComparisonAnalysis)
        .where(
            EvidenceComparisonAnalysis.activity_id == activity.id,
            EvidenceComparisonAnalysis.comparison_status == "COMPLETED",
        )
        .order_by(
            EvidenceComparisonAnalysis.created_at.desc(),
            EvidenceComparisonAnalysis.id.desc(),
        )
    )
    ai_confidence = latest_analysis.confidence_score if latest_analysis else None
    if ai_confidence is None and latest_comparison is not None:
        ai_confidence = latest_comparison.confidence * Decimal("100")
    if ai_confidence is None:
        ai_impact = 40
    elif ai_confidence >= 80:
        ai_impact = 0
    elif ai_confidence >= 60:
        ai_impact = 15
    elif ai_confidence >= 40:
        ai_impact = 30
    else:
        ai_impact = 50

    latest_assessment = db.scalar(
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
    fused_progress = latest_assessment.fused_progress if latest_assessment else None
    planned_progress = latest_assessment.planned_progress if latest_assessment else None
    progress_lag = (
        planned_progress - fused_progress
        if planned_progress is not None and fused_progress is not None
        else None
    )
    lag_impact = _progress_lag_impact(progress_lag)

    deadline_impact, days_remaining = _deadline_impact(activity, assessment_date)
    if activity.status == FieldActivityStatus.COMPLETED:
        status_impact = 0
    elif (
        activity.status == FieldActivityStatus.NOT_STARTED
        and schedule is not None
        and schedule.planned_start < assessment_date
    ):
        status_impact = 60
    elif activity.status == FieldActivityStatus.STARTED:
        status_impact = 20
    elif activity.status == FieldActivityStatus.SUBMITTED:
        status_impact = 10
    else:
        status_impact = 10

    historical = list(
        db.scalars(
            select(ProgressAssessment)
            .where(
                ProgressAssessment.activity_id == activity.id,
                ProgressAssessment.assessment_date <= assessment_date,
            )
            .order_by(
                ProgressAssessment.assessment_date.desc(),
                ProgressAssessment.id.desc(),
            )
            .limit(3)
        ).all()
    )
    trend_name, trend_impact = _trend(historical)
    factors = [
        {
            "factor": "progress_lag",
            "impact": lag_impact,
            "weight": 0.35,
            "description": (
                f"Fused progress is {_rounded(progress_lag)}% below planned progress."
                if progress_lag is not None and progress_lag > 0
                else "Fused progress is not below planned progress."
            ),
            "order": 0,
        },
        {
            "factor": "deadline",
            "impact": deadline_impact,
            "weight": 0.25,
            "description": (
                f"Activity is due in {days_remaining} days."
                if days_remaining is not None and days_remaining >= 0
                else "Scheduled finish date has passed or is unavailable."
            ),
            "order": 1,
        },
        {
            "factor": "evidence_gap",
            "impact": evidence_impact,
            "weight": 0.10,
            "description": (
                "Recent valid evidence is available."
                if evidence_impact == 0
                else "Recent field evidence is unavailable."
            ),
            "order": 2,
        },
        {
            "factor": "ai_confidence",
            "impact": ai_impact,
            "weight": 0.10,
            "description": (
                f"Latest completed AI analysis confidence is {ai_confidence}%."
                if ai_confidence is not None
                else "No completed comparison analysis is available."
            ),
            "order": 3,
        },
        {
            "factor": "activity_status",
            "impact": status_impact,
            "weight": 0.10,
            "description": f"Activity status is {activity.status.value}.",
            "order": 4,
        },
        {
            "factor": "progress_trend",
            "impact": trend_impact,
            "weight": 0.10,
            "description": f"Recent progress trend is {trend_name.lower()}.",
            "order": 5,
        },
    ]
    score = _rounded(
        Decimal(str(sum(factor["impact"] * factor["weight"] for factor in factors)))
    )
    score = max(Decimal("0"), min(Decimal("100"), score))
    risk_level = _risk_level(score)
    primary_risk = _primary_risk(factors)
    delay_estimate = predict_activity_delay(db, activity, assessment_date)
    prediction = ActivityRiskPrediction(
        project_id=activity.project_id,
        activity_id=activity.id,
        schedule_activity_id=activity.schedule_activity_id,
        comparison_id=latest_comparison.id if latest_comparison else None,
        prediction_date=assessment_date,
        risk_level=risk_level,
        risk_score=score,
        predicted_delay_days=delay_estimate.predicted_delay_days,
        confidence_score=delay_estimate.confidence_score,
        primary_risk=primary_risk,
        risk_factors=[
            {key: value for key, value in factor.items() if key != "order"}
            for factor in factors
        ],
        explanation=delay_estimate.explanation,
        model_name="BuildSync Rule-Based Risk Engine",
        model_version="1.0",
        prediction_status=RiskPredictionStatus.COMPLETED,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
