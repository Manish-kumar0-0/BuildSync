from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Evidence, User
from app.models.evidence import EvidenceType
from app.models.evidence_comparison_analysis import EvidenceComparisonAnalysis
from app.models.construction_event import ConstructionEventType
from app.models.field_activity import Activity
from app.routes.evidence import _ensure_evidence_access, _safe_evidence_path
from app.routes.evidence_comparison import VALID_STATUSES, _load_evidence, _previous
from app.schemas.vision_comparison import (
    EvidenceComparisonRequest,
    EvidenceComparisonResponse,
    VisionComparisonResult,
    VisionObservation,
)
from app.services.events.event_service import create_event
from app.services.vision.gemini_vision import (
    GeminiVisionComparisonError,
    GeminiVisionComparisonProvider,
)
from app.services.vision.comparison_service import compare_detections
from app.services.vision.opencv_service import OpenCVImageError, image_difference, load_and_prepare
from app.services.vision.yolo_service import YOLOError, detect
from app.services.progress.assessment_service import assess_activity_progress

router = APIRouter(tags=["evidence vision comparison"])


def _response(analysis: EvidenceComparisonAnalysis) -> EvidenceComparisonResponse:
    structured = next(
        (
            item for item in analysis.observations
            if item.get("category") == "STRUCTURED_VISION_COMPARISON"
        ),
        None,
    )
    return EvidenceComparisonResponse(
        comparison_id=analysis.id,
        current_evidence_id=analysis.current_evidence_id,
        previous_evidence_id=analysis.previous_evidence_id,
        comparison_status=analysis.comparison_status,
        overall_change=analysis.overall_change,
        confidence=analysis.confidence,
        construction_change_score=analysis.construction_change_score,
        absolute_progress_estimate=analysis.absolute_progress_estimate,
        absolute_progress_confidence=analysis.absolute_progress_confidence,
        observations=analysis.observations,
        possible_issues=analysis.possible_issues,
        notes=analysis.notes,
        model=analysis.model_name,
        created_at=analysis.created_at,
        detections=structured.get("detections") if structured else None,
        comparison=structured.get("comparison") if structured else None,
        opencv_difference=structured.get("opencv_difference") if structured else None,
        gemini_explanation=analysis.notes,
        limitations=structured.get("limitations", []) if structured else [],
    )


def _image_path(evidence: Evidence) -> Path:
    if evidence.evidence_type != EvidenceType.PHOTO:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only photo evidence can be compared")
    path = _safe_evidence_path(evidence.file_path)
    if not path.is_file():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Evidence image is unavailable")
    return path


@router.get(
    "/api/evidence/{evidence_id}/comparison-analysis",
    response_model=EvidenceComparisonResponse,
)
def get_latest_comparison(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceComparisonResponse:
    evidence = _load_evidence(db, evidence_id)
    _ensure_evidence_access(db, evidence, current_user)
    analysis = db.scalar(
        select(EvidenceComparisonAnalysis)
        .where(EvidenceComparisonAnalysis.current_evidence_id == evidence_id)
        .order_by(
            EvidenceComparisonAnalysis.created_at.desc(),
            EvidenceComparisonAnalysis.id.desc(),
        )
    )
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence comparison not found")
    return _response(analysis)


@router.post(
    "/api/evidence/{evidence_id}/compare-with-previous",
    response_model=EvidenceComparisonResponse,
)
def compare_with_previous(
    evidence_id: int,
    request: EvidenceComparisonRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceComparisonResponse:
    current = _load_evidence(db, evidence_id)
    if current.activity is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Evidence activity is unavailable")
    _ensure_evidence_access(db, current, current_user)
    if current.status not in VALID_STATUSES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Evidence is not valid for comparison",
        )
    previous = _previous(
        db,
        current,
        request.previous_evidence_id if request is not None else None,
    )
    if previous is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No previous valid evidence found")
    _ensure_evidence_access(db, previous, current_user)
    existing = db.scalar(
        select(EvidenceComparisonAnalysis).where(
            EvidenceComparisonAnalysis.current_evidence_id == current.id,
            EvidenceComparisonAnalysis.previous_evidence_id == previous.id,
        )
    )
    if existing is not None and not (request and request.refresh_existing):
        assessment_date = (current.captured_at or current.uploaded_at).date()
        assess_activity_progress(db, current.activity, assessment_date)
        return _response(existing)

    current_path = _image_path(current)
    previous_path = _image_path(previous)
    activity = db.scalar(
        select(Activity)
        .options(
            selectinload(Activity.project),
            selectinload(Activity.wbs),
            selectinload(Activity.boq_item),
        )
        .where(Activity.id == current.activity_id)
    )
    if activity is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity is unavailable")
    context = {
        "project": activity.project.name if activity.project else None,
        "activity": activity.name,
        "activity_description": activity.description,
        "wbs": activity.wbs.name if activity.wbs else None,
        "wbs_description": activity.wbs.description if activity.wbs else None,
        "boq_description": activity.boq_item.description if activity.boq_item else None,
        "planned_start": (
            activity.schedule_activity.planned_start
            if activity.schedule_activity
            else None
        ),
        "planned_finish": (
            activity.schedule_activity.planned_finish
            if activity.schedule_activity
            else None
        ),
        "planned_progress": (
            str(activity.schedule_activity.planned_progress)
            if activity.schedule_activity
            and activity.schedule_activity.planned_progress is not None
            else None
        ),
        "reported_progress": str(current.reported_progress) if current.reported_progress is not None else None,
        "previous_timestamp": previous.captured_at or previous.uploaded_at,
        "current_timestamp": current.captured_at or current.uploaded_at,
        "zone": activity.zone,
        "previous_evidence_notes": previous.notes,
        "current_evidence_notes": current.notes,
    }
    previous_detections: list[dict] = []
    current_detections: list[dict] = []
    detection_comparison: dict[str, list[dict]] = {}
    opencv_result: dict[str, float | int | str] | None = None
    limitations: list[str] = []
    try:
        previous_prepared = load_and_prepare(previous_path)
        current_prepared = load_and_prepare(current_path)
        previous_detections = detect(previous_prepared)
        current_detections = detect(current_prepared)
        detection_comparison = compare_detections(
            previous_detections,
            current_detections,
        )
        opencv_result = image_difference(previous_prepared, current_prepared)
        context["yolo_comparison"] = detection_comparison
        provider = GeminiVisionComparisonProvider()
        result = provider.analyze_evidence_pair(current_path, previous_path, context)
    except (OpenCVImageError, YOLOError) as exc:
        limitations.append(str(exc))
        try:
            provider = GeminiVisionComparisonProvider()
            result = provider.analyze_evidence_pair(current_path, previous_path, context)
        except GeminiVisionComparisonError as provider_exc:
            result = _metadata_comparison(current, previous, provider_exc)
    except GeminiVisionComparisonError as exc:
        result = _metadata_comparison(current, previous, exc)
    if limitations:
        result.notes = (
            f"{result.notes} " if result.notes else ""
        ) + "Visual processing was unavailable; this comparison uses recorded evidence metadata."

    analysis = existing
    if analysis is None:
        analysis = EvidenceComparisonAnalysis(
            project_id=current.project_id,
            activity_id=current.activity_id,
            current_evidence_id=current.id,
            previous_evidence_id=previous.id,
        )
        db.add(analysis)
    analysis.comparison_status = result.comparison_status
    analysis.overall_change = result.overall_change
    analysis.confidence = result.confidence
    analysis.construction_change_score = result.construction_change_score
    analysis.absolute_progress_estimate = result.absolute_progress_estimate
    analysis.absolute_progress_confidence = result.absolute_progress_confidence
    analysis.observations = [
            {
                "category": "STRUCTURED_VISION_COMPARISON",
                "detections": {
                    "previous": previous_detections,
                    "current": current_detections,
                },
                "comparison": detection_comparison,
                "opencv_difference": opencv_result,
                "limitations": limitations + [
                    "YOLO detections are model-dependent and are not construction progress measurements."
                ],
            },
            *[item.model_dump() for item in result.observations],
        ]
    analysis.possible_issues = result.possible_issues
    analysis.notes = result.notes
    analysis.model_name = provider.model_name
    db.flush()
    create_event(
        db,
        project_id=current.project_id,
        activity_id=current.activity_id,
        event_type=ConstructionEventType.EVIDENCE_COMPARISON_COMPLETED,
        title="Evidence comparison completed",
        description=(
            f"Visible progress was compared between evidence {previous.id} and "
            f"{current.id} for {activity.name}."
        ),
        event_timestamp=datetime.now(timezone.utc),
        evidence_id=current.id,
        metadata={
            "comparison_id": analysis.id,
            "previous_evidence_id": previous.id,
            "overall_change": result.overall_change,
            "confidence": result.confidence,
            "construction_change_score": result.construction_change_score,
        },
        reference_type="EvidenceComparisonAnalysis",
        reference_id=analysis.id,
    )
    db.commit()
    db.refresh(analysis)
    assessment_date = (current.captured_at or current.uploaded_at).date()
    assess_activity_progress(db, current.activity, assessment_date)
    return _response(analysis)


def _metadata_comparison(
    current: Evidence,
    previous: Evidence,
    error: GeminiVisionComparisonError,
) -> VisionComparisonResult:
    previous_progress = float(previous.reported_progress or 0)
    current_progress = float(current.reported_progress or 0)
    delta = current_progress - previous_progress
    if delta > 0:
        change = "INCREASED"
        overall = "PROGRESS"
    elif delta < 0:
        change = "DECREASED"
        overall = "REGRESSION"
    else:
        change = "UNCHANGED"
        overall = "NO_REPORTED_CHANGE"
    return VisionComparisonResult(
        comparison_status="COMPLETED",
        overall_change=overall,
        confidence=0.6,
        construction_change_score=max(0, min(1, abs(delta) / 100)),
        absolute_progress_estimate=current_progress,
        absolute_progress_confidence=0.6,
        observations=[
            VisionObservation(
                category="REPORTED_PROGRESS",
                observation=(
                    f"Reported progress changed from {previous_progress:.1f}% "
                    f"to {current_progress:.1f}%."
                ),
                change=change,
                confidence=0.6,
            )
        ],
        possible_issues=[],
        notes=f"Vision provider unavailable: {error}",
    )
