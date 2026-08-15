from abc import ABC, abstractmethod

from app.schemas.llm import AnalysisRequest
from app.schemas.semantic import ValidatedAnalysis


class LLMAdapter(ABC):
    @abstractmethod
    def analyze(self, request: AnalysisRequest) -> ValidatedAnalysis:
        """Return an analysis that has passed provider-output validation."""
