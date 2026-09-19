from abc import ABC, abstractmethod

from app.schemas.assistant import AssistantContext, AssistantProviderResult


class AssistantProvider(ABC):
    @abstractmethod
    def generate_answer(
        self, question: str, context: AssistantContext
    ) -> AssistantProviderResult:
        """Generate a grounded answer from supplied context only."""
