import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.services.ai.base import AIAnalysisResult, VisionProvider


class GeminiVisionError(RuntimeError):
    """A safe, provider-level error suitable for an API failure response."""


class _GeminiAnalysis(BaseModel):
    estimated_progress: float = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=100)
    detected_elements: list[dict[str, Any]]
    observations: list[str]
    discrepancies: list[str]


CONSTRUCTION_ANALYSIS_PROMPT = """You are analyzing visual evidence from a construction project.
Return only valid JSON matching the requested schema.

Analyze visible construction work, construction elements, apparent completion level,
visible progress indicators, possible inconsistencies, and evidence quality. Do not
claim certainty when the evidence is unclear. Estimate visible progress independently
from the field-reported progress. This estimate is not verified actual progress.

Construction context:
{context}

Use concise observations and discrepancies. Include evidence quality limitations in
observations when the image is blurry, incomplete, poorly framed, or otherwise weak.
"""


def _context_value(value: Any) -> str:
    return str(value) if value is not None else "Not provided"


def _activity_context(activity: Any, wbs: Any, boq: Any) -> str:
    project = getattr(activity, "project", None)
    schedule = getattr(activity, "schedule_activity", None)
    return "\n".join(
        [
            f"Project: {_context_value(getattr(project, 'name', None))}",
            f"WBS: {_context_value(getattr(wbs, 'name', None))}",
            f"BOQ: {_context_value(getattr(boq, 'description', None))}",
            f"Schedule Activity: {_context_value(getattr(schedule, 'name', None))}",
            f"Field Activity: {_context_value(getattr(activity, 'name', None))}",
            f"Reported Progress: {_context_value(getattr(activity, 'progress_percentage', None))}%",
        ]
    )


class GeminiVisionService(VisionProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.model_name = model_name or settings.gemini_model
        key = api_key or settings.gemini_api_key
        if not key:
            raise GeminiVisionError("Gemini API credentials are not configured")
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiVisionError("Gemini provider is not installed") from exc
        self._types = genai.types
        try:
            self._client = genai.Client(api_key=key)
        except Exception as exc:
            raise GeminiVisionError("Gemini provider could not be initialized") from exc

    def analyze(
        self,
        evidence_path: Path,
        activity: Any,
        wbs: Any = None,
        boq: Any = None,
    ) -> AIAnalysisResult:
        if evidence_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise GeminiVisionError("Only photo evidence is supported by Gemini analysis")
        try:
            image_bytes = evidence_path.read_bytes()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }[evidence_path.suffix.lower()]
            prompt = CONSTRUCTION_ANALYSIS_PROMPT.format(
                context=_activity_context(activity, wbs, boq)
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[
                    self._types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_GeminiAnalysis,
                ),
            )
            raw_response = getattr(response, "text", None)
            if not raw_response:
                raise GeminiVisionError("Gemini returned an empty analysis")
            parsed = _GeminiAnalysis.model_validate(json.loads(raw_response))
        except GeminiVisionError:
            raise
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise GeminiVisionError("Gemini returned an invalid analysis") from exc
        except Exception as exc:
            raise GeminiVisionError("Gemini analysis could not be completed") from exc

        return AIAnalysisResult(
            estimated_progress=parsed.estimated_progress,
            confidence_score=parsed.confidence_score,
            detected_elements=parsed.detected_elements,
            observations=parsed.observations,
            discrepancies=parsed.discrepancies,
        )
