from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AIAnalysisResult:
    estimated_progress: float
    confidence_score: float
    detected_elements: list[dict[str, Any]]
    observations: list[str]
    discrepancies: list[Any]


class VisionProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def analyze(
        self,
        evidence_path: Path,
        activity: Any,
        wbs: Any = None,
        boq: Any = None,
    ) -> AIAnalysisResult:
        """Analyze an evidence file using the provider."""
