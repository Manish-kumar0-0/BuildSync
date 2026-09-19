from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.planning import ProjectStatus
from app.models.recovery import RecommendationPriority, RecommendationStatus, RecommendationType
from app.models.risk_prediction import PrimaryRisk, RiskLevel


class DashboardProject(BaseModel):
    id: int
    name: str
    status: ProjectStatus


class DashboardProgress(BaseModel):
    planned: Decimal | None
    actual: Decimal | None
    variance: Decimal | None


class DashboardActivities(BaseModel):
    total: int
    completed: int
    in_progress: int
    not_started: int
    submitted: int


class DelayedActivitySummary(BaseModel):
    activity_id: int
    activity_name: str
    planned_progress: Decimal | None
    fused_progress: Decimal | None
    variance: Decimal
    predicted_delay_days: Decimal | None


class DashboardDelay(BaseModel):
    delayed_count: int
    top_delayed_activities: list[DelayedActivitySummary]


class RiskActivitySummary(BaseModel):
    activity_id: int
    activity_name: str
    risk_level: RiskLevel
    risk_score: Decimal
    primary_risk: PrimaryRisk
    predicted_delay_days: Decimal | None


class DashboardRisk(BaseModel):
    low: int
    medium: int
    high: int
    critical: int
    top_risk_activities: list[RiskActivitySummary]


class DashboardEvidence(BaseModel):
    total: int
    pending_verification: int
    verified: int
    rejected: int


class ActiveRecoverySummary(BaseModel):
    id: int
    activity_id: int
    type: RecommendationType
    priority: RecommendationPriority
    title: str
    status: RecommendationStatus


class DashboardRecovery(BaseModel):
    suggested: int
    accepted: int
    implemented: int
    active_recommendations: list[ActiveRecoverySummary]


class ProjectDashboardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project: DashboardProject
    progress: DashboardProgress
    activities: DashboardActivities
    delay: DashboardDelay
    risk: DashboardRisk
    evidence: DashboardEvidence
    recovery: DashboardRecovery


class ProgressTimelinePoint(BaseModel):
    date: date
    planned_progress: Decimal
    actual_progress: Decimal


class ProgressTimelineResponse(BaseModel):
    project_id: int
    data: list[ProgressTimelinePoint]


class ProgressTrendSnapshot(BaseModel):
    planned: Decimal | None
    actual: Decimal | None
    variance: Decimal | None


class ProgressTrend(BaseModel):
    direction: str
    change: Decimal | None


class ProgressTrendResponse(BaseModel):
    current: ProgressTrendSnapshot
    trend: ProgressTrend
    history: list[ProgressTimelinePoint]


class RiskTimelinePoint(BaseModel):
    date: date
    low: int
    medium: int
    high: int
    critical: int


class RiskTimelineResponse(BaseModel):
    project_id: int
    data: list[RiskTimelinePoint]


class HighestDelayActivity(BaseModel):
    activity_id: int
    activity_name: str
    predicted_delay_days: Decimal


class DelaySummaryResponse(BaseModel):
    total_delayed_activities: int
    total_predicted_delay_days: Decimal
    highest_delay_activity: HighestDelayActivity | None


class RecoveryTimelineItem(BaseModel):
    activity_id: int
    type: RecommendationType
    priority: RecommendationPriority
    status: RecommendationStatus


class RecoverySummaryResponse(BaseModel):
    suggested: int
    accepted: int
    implemented: int
    rejected: int
    top_recommendations: list[RecoveryTimelineItem]


class CombinedTimelinePoint(BaseModel):
    date: date
    planned_progress: Decimal | None
    actual_progress: Decimal | None
    variance: Decimal | None
    high_risk_activities: int
    critical_risk_activities: int
    predicted_delay_days: Decimal


class CombinedTimelineResponse(BaseModel):
    project_id: int
    events: list[CombinedTimelinePoint]
