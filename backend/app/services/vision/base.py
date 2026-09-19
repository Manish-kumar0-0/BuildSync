from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.schemas.vision_comparison import VisionComparisonResult


class VisionComparisonProvider(ABC):
    @abstractmethod
    def analyze_evidence_pair(
        self,
        current_image: Path,
        previous_image: Path,
        context: dict[str, Any],
    ) -> VisionComparisonResult:
        """Analyze two construction images using only visible evidence."""
