import re

from app.models.analysis import SlotType
from app.schemas.llm import AnalysisRequest, SourceSegment
from app.schemas.semantic import SemanticSlotPayload, ValidatedAnalysis
from app.services.llm.base import LLMAdapter


class RuleBasedLLMAdapter(LLMAdapter):
    """Deterministic fixture-friendly adapter used when no provider is configured."""

    def analyze(self, request: AnalysisRequest) -> ValidatedAnalysis:
        slots = [slot for segment in request.segments for slot in self._analyze_segment(segment)]
        return ValidatedAnalysis(slots=slots)

    def _analyze_segment(self, segment: SourceSegment) -> list[SemanticSlotPayload]:
        text = segment.text.strip()
        slots = [self._slot(SlotType.FACT, text, segment.id, confidence=0.6, importance=0.5)]
        lowered = text.lower()
        if any(term in lowered for term in ("action:", "todo", "deploy", "implement", "execute")):
            slots.append(self._slot(SlotType.ACTION, text, segment.id, confidence=0.8, importance=0.8))
        deadline = re.search(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.IGNORECASE)
        if deadline:
            slots.append(self._slot(SlotType.DEADLINE, deadline.group(0), segment.id, confidence=0.9, importance=0.7))
        if any(term in lowered for term in ("risk", "unknown", "assumption")):
            slots.append(self._slot(SlotType.RISK_UNKNOWN, text, segment.id, confidence=0.7, importance=0.7))
        return slots

    @staticmethod
    def _slot(slot: SlotType, text: str, source_segment_id: str, *, confidence: float, importance: float) -> SemanticSlotPayload:
        return SemanticSlotPayload(slot=slot, text=text, source_segment_id=source_segment_id, confidence=confidence, importance=importance)
