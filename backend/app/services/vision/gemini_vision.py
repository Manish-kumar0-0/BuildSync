import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.vision_comparison import VisionComparisonResult
from app.services.vision.base import VisionComparisonProvider

logger = logging.getLogger(__name__)


class GeminiVisionComparisonError(RuntimeError):
    """A safe provider error suitable for an API response."""


COMPARISON_PROMPT = """You are comparing two construction site images.
IMAGE 1 is PREVIOUS EVIDENCE. IMAGE 2 is CURRENT EVIDENCE.

Return only JSON matching the requested schema. Report only visually observable changes between the images. Do not invent hidden
work, exact worker counts, measurements, or unsupported numerical claims. Use
UNCLEAR when a change cannot be confidently determined. Distinguish visible
observations from inference.

Estimate the absolute completion percentage of the specified activity only
when the images and the supplied activity context provide a defensible basis.
This is the completion of the current activity, not the amount of visible
change between the two images. Return absolute_progress_estimate as a
percentage from 0 to 100 and absolute_progress_confidence from 0 to 100 only
when that estimate is visually supportable. Otherwise return both fields as
null. Never derive either field from planned progress, reported progress,
confidence, or construction_change_score.

Construction context:
{context}
"""


class GeminiVisionComparisonProvider(VisionComparisonProvider):
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        key = api_key or settings.gemini_api_key
        if not key:
            raise GeminiVisionComparisonError("Gemini API credentials are not configured")
        self.model_name = (
            model_name or settings.gemini_vision_model or settings.gemini_model
        )
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiVisionComparisonError("Gemini provider is not installed") from exc
        self._types = genai.types
        try:
            self._client = genai.Client(api_key=key)
        except Exception as exc:
            raise GeminiVisionComparisonError("Gemini provider could not be initialized") from exc

    def analyze_evidence_pair(
        self,
        current_image: Path,
        previous_image: Path,
        context: dict[str, Any],
    ) -> VisionComparisonResult:
        allowed = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        if current_image.suffix.lower() not in allowed or previous_image.suffix.lower() not in allowed:
            raise GeminiVisionComparisonError("Only photo evidence is supported")
        try:
            prompt = COMPARISON_PROMPT.format(context=json.dumps(context, default=str))
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt,
                    self._types.Part.from_bytes(
                        data=previous_image.read_bytes(),
                        mime_type=allowed[previous_image.suffix.lower()],
                    ),
                    self._types.Part.from_bytes(
                        data=current_image.read_bytes(),
                        mime_type=allowed[current_image.suffix.lower()],
                    ),
                ],
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VisionComparisonResult,
                ),
            )
        except OSError as exc:
            logger.error(
                "Gemini comparison diagnostic category=PROVIDER_EXCEPTION "
                "exception_type=%s status=%s",
                type(exc).__name__,
                _safe_status(exc),
            )
            raise GeminiVisionComparisonError("Gemini comparison could not be completed") from exc
        except Exception as exc:
            logger.error(
                "Gemini comparison diagnostic category=PROVIDER_EXCEPTION "
                "exception_type=%s status=%s",
                type(exc).__name__,
                _safe_status(exc),
            )
            raise GeminiVisionComparisonError("Gemini comparison could not be completed") from exc

        raw_response = getattr(response, "text", None)
        if not raw_response:
            logger.error(
                "Gemini comparison diagnostic category=EMPTY_RESPONSE response_text_present=False"
            )
            raise GeminiVisionComparisonError("Gemini returned an empty comparison")
        logger.info(
            "Gemini comparison diagnostic category=RESPONSE_RECEIVED response_text_present=True"
        )
        try:
            parsed_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.error(
                "Gemini comparison diagnostic category=JSON_PARSE_ERROR "
                "response_text_present=True exception_type=%s",
                type(exc).__name__,
            )
            raise GeminiVisionComparisonError("Gemini returned an invalid comparison") from exc
        logger.info(
            "Gemini comparison diagnostic category=JSON_PARSED response_text_present=True "
            "json_parsing_succeeded=True"
        )
        try:
            result = VisionComparisonResult.model_validate(parsed_response)
        except ValidationError as exc:
            logger.error(
                "Gemini comparison diagnostic category=SCHEMA_VALIDATION_ERROR "
                "json_parsing_succeeded=True schema_validation_succeeded=False "
                "exception_type=%s",
                type(exc).__name__,
            )
            raise GeminiVisionComparisonError("Gemini returned an invalid comparison") from exc
        logger.info(
            "Gemini comparison diagnostic category=SUCCESS response_text_present=True "
            "json_parsing_succeeded=True schema_validation_succeeded=True"
        )

        for observation in result.observations:
            if observation.confidence < 0.5:
                observation.change = "UNCLEAR"
        return result


def _safe_status(exc: Exception) -> int | str:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    return status if isinstance(status, (int, str)) else "unavailable"
