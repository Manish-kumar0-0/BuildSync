from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_analysis import AIAnalysis, AIAnalysisStatus
from app.models.evidence import Evidence
from app.services.ai.base import AIAnalysisResult, VisionProvider
from app.services.ai.mock_vision import MockVisionService
from app.services.ai.gemini_vision import GeminiVisionService


class _ValidatedAnalysisResult(BaseModel):
    estimated_progress: Decimal = Field(ge=0, le=100)
    confidence_score: Decimal = Field(ge=0, le=100)
    detected_elements: list[dict[str, Any]]
    observations: list[str]
    discrepancies: list[Any]


def _provider_for_name(provider_name: str) -> VisionProvider:
    if provider_name == "mock":
        return MockVisionService()
    if provider_name == "gemini":
        return GeminiVisionService()
    raise ValueError(f"Unsupported AI provider: {provider_name}")


def _stored_path(file_path: str) -> Path:
    return (Path(__file__).resolve().parents[3] / file_path).resolve()


class VisionService:
    def __init__(self, provider: VisionProvider | None = None):
        self.provider = provider or _provider_for_name(settings.ai_provider)

    def analyze_evidence(
        self,
        db: Session,
        evidence: Evidence,
        activity: Any,
        wbs: Any = None,
        boq: Any = None,
    ) -> AIAnalysis:
        if evidence is None:
            raise ValueError("Evidence is required")
        evidence_path = _stored_path(evidence.file_path)
        if not evidence_path.is_file():
            raise FileNotFoundError("Evidence file is not available for analysis")

        started_at = datetime.now(timezone.utc)
        analysis = AIAnalysis(
            evidence_id=evidence.id,
            analysis_status=AIAnalysisStatus.PROCESSING,
            provider=self.provider.provider_name,
            model_name=self.provider.model_name,
            processing_started_at=started_at,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        try:
            result = self.provider.analyze(evidence_path, activity, wbs, boq)
            validated = _ValidatedAnalysisResult.model_validate(
                result.__dict__
                if isinstance(result, AIAnalysisResult)
                else result
            )
            analysis.estimated_progress = validated.estimated_progress
            analysis.confidence_score = validated.confidence_score
            analysis.detected_elements = validated.detected_elements
            analysis.observations = "\n".join(validated.observations)
            analysis.discrepancies = validated.discrepancies
            analysis.analysis_status = AIAnalysisStatus.COMPLETED
            analysis.processing_completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(analysis)
            return analysis
        except Exception as exc:
            db.rollback()
            analysis = db.get(AIAnalysis, analysis.id)
            if analysis is None:
                raise RuntimeError("AI analysis record was not found after failure") from exc
            analysis.analysis_status = AIAnalysisStatus.FAILED
            analysis.observations = f"AI analysis failed: {type(exc).__name__}"
            analysis.processing_completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(analysis)
            raise


def analyze_evidence(
    db: Session,
    evidence: Evidence,
    activity: Any,
    wbs: Any = None,
    boq: Any = None,
) -> AIAnalysis:
    return VisionService().analyze_evidence(db, evidence, activity, wbs, boq)
