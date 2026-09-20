import json
import logging

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.assistant import AssistantContext, AssistantProviderResult
from app.services.assistant.providers.base import AssistantProvider

logger = logging.getLogger(__name__)


class GeminiAssistantError(RuntimeError):
    """A safe provider error without credential or stack-trace details."""


class GeminiAssistantProvider(AssistantProvider):
    def __init__(self, api_key: str | None = None):
        key = api_key or settings.gemini_api_key
        if not key:
            raise GeminiAssistantError("Gemini API credentials are not configured")
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiAssistantError("Gemini provider is not installed") from exc
        self._types = genai.types
        try:
            self._client = genai.Client(
                api_key=key,
                http_options=genai.types.HttpOptions(
                    timeout=settings.gemini_request_timeout_ms,
                ),
            )
        except Exception as exc:
            raise GeminiAssistantError("Gemini provider could not be initialized") from exc

    def generate_answer(
        self, question: str, context: AssistantContext
    ) -> AssistantProviderResult:
        prompt = (
            "You are the BuildSync Project Assistant. Answer only from the supplied "
            "BuildSync context. Never invent facts. If the context does not answer "
            "the question, say that the information is unavailable. Distinguish "
            "reported progress from AI-estimated progress, predictions from confirmed "
            "events, and recommendations from implemented actions. Do not make "
            "safety-critical decisions or propose automatic system changes. Keep the "
            "answer concise and operational. Return only JSON with answer and "
            "source_ids, confidence (SUPPORTED, PARTIALLY_SUPPORTED, or "
            "INSUFFICIENT_DATA), where source_ids are IDs of records used from "
            "the context.\n\n"
            f"Question: {question}\n"
            f"Context: {json.dumps(context.model_dump(mode='json'), default=str)}"
        )
        try:
            response = self._client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AssistantProviderResult,
                ),
            )
            raw_response = getattr(response, "text", None)
            if not raw_response:
                raise GeminiAssistantError("Gemini returned an empty answer")
            return AssistantProviderResult.model_validate(json.loads(raw_response))
        except GeminiAssistantError:
            raise
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(
                "Gemini assistant diagnostic category=INVALID_RESPONSE "
                "exception_type=%s",
                type(exc).__name__,
            )
            raise GeminiAssistantError("Gemini returned an invalid answer") from exc
        except Exception as exc:
            status = _safe_status(exc)
            logger.error(
                "Gemini assistant diagnostic category=PROVIDER_EXCEPTION "
                "exception_type=%s status=%s",
                type(exc).__name__,
                status,
            )
            raise GeminiAssistantError(
                _provider_failure_message(exc, status)
            ) from exc


def _safe_status(exc: Exception) -> int | str:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    return status if isinstance(status, (int, str)) else "unavailable"


def _provider_failure_message(exc: Exception, status: int | str) -> str:
    exception_name = type(exc).__name__.lower()
    if "timeout" in exception_name or "timeout" in str(exc).lower():
        return "Gemini request timed out; increase GEMINI_REQUEST_TIMEOUT_MS or check provider availability"
    if status != "unavailable":
        return f"Gemini request was rejected (provider status {status})"
    return "Gemini request failed before a provider response"
