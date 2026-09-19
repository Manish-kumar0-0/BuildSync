from pathlib import Path
from typing import Any

from app.services.ai.base import AIAnalysisResult, VisionProvider


class MockVisionService(VisionProvider):
    """Deterministic development provider; this is not real AI analysis."""

    provider_name = "mock"
    model_name = "mock-vision-development"

    def analyze(
        self,
        evidence_path: Path,
        activity: Any,
        wbs: Any = None,
        boq: Any = None,
    ) -> AIAnalysisResult:
        return AIAnalysisResult(
            estimated_progress=60,
            confidence_score=85,
            detected_elements=[
                {"element": "reinforcement", "confidence": 91}
            ],
            observations=[
                "Reinforcement work appears visible in the submitted evidence."
            ],
            discrepancies=[],
        )
