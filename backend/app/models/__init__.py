"""SQLAlchemy models."""

from app.models.planning import (
    ActivityStatus,
    BOQItem,
    PlannedProgress,
    Project,
    ProjectStatus,
    ScheduleActivity,
    WBS,
    WBSStatus, ScheduleApprovalStatus,
)
from app.models.user import User, UserRole
from app.models.field_activity import (
    Activity,
    ActivityAssignment,
    AssignmentRole,
    AssignmentStatus,
    FieldActivityStatus,
)
from app.models.evidence import Evidence, EvidenceStatus, EvidenceType
from app.models.evidence_verification import (
    EvidenceVerification,
    EvidenceVerificationDecision,
)
from app.models.ai_analysis import AIAnalysis, AIAnalysisStatus
from app.models.progress_assessment import (
    ProgressAssessment,
    ProgressAssessmentStatus,
)
from app.models.risk_prediction import (
    ActivityRiskPrediction,
    PrimaryRisk,
    RiskLevel,
    RiskPredictionStatus,
)
from app.models.recovery import (
    ImplementationEffort,
    RecommendationImpact,
    RecommendationPriority,
    RecommendationStatus,
    RecommendationType,
    RecoveryRecommendation,
)
from app.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)
from app.models.construction_event import ConstructionEvent, ConstructionEventType
from app.models.project_memory import (
    MemoryImportance,
    MemoryType,
    ProjectMemory,
)
from app.models.evidence_snapshot import EvidenceSnapshot
from app.models.evidence_comparison_analysis import EvidenceComparisonAnalysis
from app.models.site_disruption import (
    SiteDisruption,
    SiteDisruptionSeverity,
    SiteDisruptionSource,
    SiteDisruptionType,
)
from app.models.resource_tracking import (
    Equipment, EquipmentAssignment, EquipmentIssue, EquipmentIssueSeverity, EquipmentUsageRecord,
    EquipmentStatus, MaterialItem, MaterialMovement, MaterialMovementType,
    Vehicle, VehicleStatus, VehicleTrip, VehicleTripStatus,
)
from app.models.workforce import (
    AttendanceRecord, AttendanceStatus, Crew, CrewMember, WorkerAssignment,
    WorkforceAssignment, WorkforceAssignmentStatus,
)
from app.models.safety import (
    PPEInspection, SafetyIncident, SafetyIncidentSeverity, SafetyIncidentStatus, SafetyIncidentType,
)
from app.models.quality import (
    InspectionStatus, InspectionType, QualityDefect, QualityDefectStatus,
    QualityInspection, QualitySeverity,
)
from app.models.project_admin import (
    AuditLog, ProjectAssignmentStatus, ProjectConfiguration,
    ProjectUserAssignment, ProjectZone,
)
from app.models.password_reset import PasswordReset
from app.models.activity_measured_progress import (
    ActivityMeasuredProgress,
    MeasuredProgressVerificationStatus,
)

__all__ = [
    "ActivityStatus",
    "Activity",
    "ActivityAssignment",
    "AssignmentRole",
    "AssignmentStatus",
    "BOQItem",
    "Evidence",
    "EvidenceStatus",
    "EvidenceType",
    "EvidenceVerification",
    "EvidenceVerificationDecision",
    "AIAnalysis",
    "AIAnalysisStatus",
    "ProgressAssessment",
    "ProgressAssessmentStatus",
    "ActivityRiskPrediction",
    "PrimaryRisk",
    "RiskLevel",
    "RiskPredictionStatus",
    "ImplementationEffort",
    "RecommendationImpact",
    "RecommendationPriority",
    "RecommendationStatus",
    "RecommendationType",
    "RecoveryRecommendation",
    "Notification",
    "NotificationPriority",
    "NotificationType",
    "ConstructionEvent",
    "ConstructionEventType",
    "MemoryImportance",
    "MemoryType",
    "ProjectMemory",
    "EvidenceSnapshot",
    "EvidenceComparisonAnalysis",
    "SiteDisruption",
    "SiteDisruptionSeverity",
    "SiteDisruptionSource",
    "SiteDisruptionType",
    "Equipment",
    "EquipmentAssignment",
    "EquipmentIssue",
    "EquipmentIssueSeverity",
    "EquipmentUsageRecord",
    "EquipmentStatus",
    "MaterialItem",
    "MaterialMovement",
    "MaterialMovementType",
    "Vehicle",
    "VehicleStatus",
    "VehicleTrip",
    "VehicleTripStatus",
    "AttendanceRecord",
    "AttendanceStatus",
    "Crew",
    "CrewMember",
    "WorkerAssignment",
    "WorkforceAssignment",
    "WorkforceAssignmentStatus",
    "SafetyIncident",
    "SafetyIncidentSeverity",
    "SafetyIncidentStatus",
    "SafetyIncidentType",
    "PPEInspection",
    "InspectionStatus",
    "InspectionType",
    "QualityDefect",
    "QualityDefectStatus",
    "QualityInspection",
    "QualitySeverity",
    "AuditLog",
    "ProjectAssignmentStatus",
    "ProjectConfiguration",
    "ProjectUserAssignment",
    "ProjectZone",
    "PlannedProgress",
    "Project",
    "ProjectStatus",
    "ScheduleActivity",
    "ScheduleApprovalStatus",
    "User",
    "UserRole",
    "WBS",
    "WBSStatus",
    "PasswordReset",
    "ActivityMeasuredProgress",
    "MeasuredProgressVerificationStatus",
]
