from app.core.config import settings
from app.schemas.assistant import AssistantContext, AssistantProviderResult
from app.services.assistant.providers.gemini import (
    GeminiAssistantError,
    GeminiAssistantProvider,
)


class AssistantConfigurationError(RuntimeError):
    """The assistant provider is not configured."""


class AssistantProviderError(RuntimeError):
    """The assistant provider failed safely."""


def _provider():
    if settings.ai_provider != "gemini":
        raise AssistantConfigurationError(
            "Project Assistant requires AI_PROVIDER=gemini"
        )
    try:
        return GeminiAssistantProvider()
    except GeminiAssistantError as exc:
        raise AssistantConfigurationError(str(exc)) from exc


def generate_project_answer(
    question: str, context: AssistantContext
) -> AssistantProviderResult:
    try:
        result = _provider().generate_answer(question, context)
    except AssistantConfigurationError:
        raise
    except GeminiAssistantError as exc:
        raise AssistantProviderError(str(exc)) from exc
    valid_ids = {source.id for source in context.sources}
    if context.sources and not result.source_ids:
        raise AssistantProviderError("Assistant returned no source references")
    if any(source_id not in valid_ids for source_id in result.source_ids):
        raise AssistantProviderError("Assistant returned an unknown source reference")
    return result
