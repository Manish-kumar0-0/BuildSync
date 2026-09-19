from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.field_activity import Activity
from app.models.recovery import (
    ImplementationEffort,
    RecommendationImpact,
    RecommendationPriority,
    RecommendationStatus,
    RecommendationType,
    RecoveryRecommendation,
)
from app.models.risk_prediction import ActivityRiskPrediction, PrimaryRisk, RiskLevel


@dataclass(frozen=True)
class _Rule:
    recommendation_type: RecommendationType
    title: str
    description: str
    expected_impact: RecommendationImpact
    implementation_effort: ImplementationEffort


RULES = {
    RecommendationType.ADD_WORKFORCE: _Rule(
        RecommendationType.ADD_WORKFORCE,
        "Increase workforce",
        "Consider increasing the assigned workforce to recover lost progress.",
        RecommendationImpact.HIGH,
        ImplementationEffort.MEDIUM,
    ),
    RecommendationType.EXTEND_SHIFT: _Rule(
        RecommendationType.EXTEND_SHIFT,
        "Extend working hours",
        "Consider an additional shift or extended working hours after checking site safety and labor availability.",
        RecommendationImpact.HIGH,
        ImplementationEffort.MEDIUM,
    ),
    RecommendationType.ADD_EQUIPMENT: _Rule(
        RecommendationType.ADD_EQUIPMENT,
        "Add equipment",
        "Consider providing additional equipment after confirming availability and site suitability.",
        RecommendationImpact.MEDIUM,
        ImplementationEffort.HIGH,
    ),
    RecommendationType.EXPEDITE_MATERIAL: _Rule(
        RecommendationType.EXPEDITE_MATERIAL,
        "Expedite material",
        "Consider expediting required materials after confirming procurement and quality requirements.",
        RecommendationImpact.HIGH,
        ImplementationEffort.MEDIUM,
    ),
    RecommendationType.RESEQUENCE_ACTIVITY: _Rule(
        RecommendationType.RESEQUENCE_ACTIVITY,
        "Resequence activity",
        "Consider resequencing dependent work to reduce the effect of the missed milestone.",
        RecommendationImpact.MEDIUM,
        ImplementationEffort.MEDIUM,
    ),
    RecommendationType.INCREASE_MONITORING: _Rule(
        RecommendationType.INCREASE_MONITORING,
        "Increase monitoring",
        "Increase field monitoring and progress updates to improve execution visibility.",
        RecommendationImpact.MEDIUM,
        ImplementationEffort.LOW,
    ),
    RecommendationType.QUALITY_REVIEW: _Rule(
        RecommendationType.QUALITY_REVIEW,
        "Conduct quality review",
        "Conduct a quality review before further recovery work proceeds.",
        RecommendationImpact.HIGH,
        ImplementationEffort.MEDIUM,
    ),
    RecommendationType.SAFETY_REVIEW: _Rule(
        RecommendationType.SAFETY_REVIEW,
        "Conduct safety review",
        "Conduct a safety review before changing work methods, shifts, or resources.",
        RecommendationImpact.HIGH,
        ImplementationEffort.MEDIUM,
    ),
    RecommendationType.NO_ACTION: _Rule(
        RecommendationType.NO_ACTION,
        "No immediate action",
        "No deterministic recovery action is indicated by the current risk prediction.",
        RecommendationImpact.LOW,
        ImplementationEffort.LOW,
    ),
}


def _priority(risk_level: RiskLevel) -> RecommendationPriority:
    return RecommendationPriority(risk_level.value)


def _has_progress_lag(risk_prediction: ActivityRiskPrediction) -> bool:
    return any(
        factor.get("factor") == "progress_lag" and factor.get("impact", 0) >= 60
        for factor in (risk_prediction.risk_factors or [])
    )


def generate_recovery_recommendations(
    db: Session,
    activity: Activity,
    risk_prediction: ActivityRiskPrediction,
) -> list[RecoveryRecommendation]:
    types: list[RecommendationType] = []
    if _has_progress_lag(risk_prediction):
        types.append(RecommendationType.ADD_WORKFORCE)
    if (
        risk_prediction.predicted_delay_days is not None
        and risk_prediction.predicted_delay_days >= 7
    ):
        types.append(RecommendationType.EXTEND_SHIFT)
    primary_rules = {
        PrimaryRisk.EQUIPMENT: RecommendationType.ADD_EQUIPMENT,
        PrimaryRisk.MATERIAL: RecommendationType.EXPEDITE_MATERIAL,
        PrimaryRisk.MISSED_MILESTONE: RecommendationType.RESEQUENCE_ACTIVITY,
        PrimaryRisk.QUALITY: RecommendationType.QUALITY_REVIEW,
        PrimaryRisk.SAFETY: RecommendationType.SAFETY_REVIEW,
    }
    if risk_prediction.primary_risk in primary_rules:
        types.append(primary_rules[risk_prediction.primary_risk])
    if risk_prediction.confidence_score < 60 or risk_prediction.primary_risk in {
        PrimaryRisk.LOW_AI_CONFIDENCE,
        PrimaryRisk.INSUFFICIENT_EVIDENCE,
    }:
        types.append(RecommendationType.INCREASE_MONITORING)
    if not types:
        types.append(RecommendationType.NO_ACTION)

    unique_types = list(dict.fromkeys(types))
    priority = _priority(risk_prediction.risk_level)
    created: list[RecoveryRecommendation] = []
    for recommendation_type in unique_types:
        active = db.scalar(
            select(RecoveryRecommendation).where(
                RecoveryRecommendation.activity_id == activity.id,
                RecoveryRecommendation.risk_prediction_id == risk_prediction.id,
                RecoveryRecommendation.recommendation_type == recommendation_type,
                RecoveryRecommendation.status.in_(
                    [RecommendationStatus.SUGGESTED, RecommendationStatus.ACCEPTED]
                ),
            )
        )
        if active is not None:
            created.append(active)
            continue
        rule = RULES[recommendation_type]
        recommendation = RecoveryRecommendation(
            project_id=activity.project_id,
            activity_id=activity.id,
            risk_prediction_id=risk_prediction.id,
            recommendation_type=rule.recommendation_type,
            priority=priority,
            title=rule.title,
            description=rule.description,
            expected_impact=rule.expected_impact,
            estimated_cost_impact=None,
            implementation_effort=rule.implementation_effort,
            status=RecommendationStatus.SUGGESTED,
        )
        db.add(recommendation)
        created.append(recommendation)
    db.commit()
    for recommendation in created:
        db.refresh(recommendation)
    return created
