from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun, AnalysisStatus, Gap, QualityCategory, QualityLabel, Relation, SemanticSlot, Severity
from app.models.document import Document
from app.schemas.diagnosis import Diagnosis, QualityMetrics
from app.services.signal.classification import classify_segment
from app.services.signal.gaps import find_gaps, gap_description
from app.services.signal.redundancy import find_redundant_segments
from app.services.signal.scoring import actionability_score, decision_completeness, document_signal_score, evidence_coverage, generic_ratio, redundancy_ratio, signal_ratio


class DiagnosisService:
    """Compute and persist advisory quality labels and gaps for a semantic run."""

    def diagnose_document(self, session: Session, document_id: str) -> Diagnosis:
        document = session.get(Document, document_id)
        if document is None:
            raise LookupError(f"Document {document_id} was not found")
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.document_id == document_id, AnalysisRun.status == AnalysisStatus.COMPLETED).order_by(AnalysisRun.created_at.desc()))
        if run is None:
            raise LookupError("Document has no completed analysis")
        slots = list(session.scalars(select(SemanticSlot).where(SemanticSlot.analysis_run_id == run.id)))
        relations = list(session.scalars(select(Relation).join(SemanticSlot, Relation.from_slot_id == SemanticSlot.id).where(SemanticSlot.analysis_run_id == run.id)))
        labels = self._persist_labels(session, run, document, slots)
        gaps = find_gaps(document.purpose.value if document.purpose else "EXPLAIN", slots)
        self._persist_gaps(session, run, document, gaps)
        metrics = self._metrics(document, slots, relations, labels)
        session.commit()
        return Diagnosis(analysis_run_id=run.id, metrics=metrics, gaps=gaps, explanations=self._explanations(labels, gaps))

    def _persist_labels(self, session: Session, run: AnalysisRun, document: Document, slots: list[SemanticSlot]) -> list[QualityLabel]:
        existing = list(session.scalars(select(QualityLabel).where(QualityLabel.analysis_run_id == run.id)))
        if existing:
            return existing
        redundant = dict(find_redundant_segments((segment.id, segment.text) for segment in document.segments))
        labels = []
        for segment in document.segments:
            if segment.id in redundant:
                category, score, reason = QualityCategory.REDUNDANT, 1.0, redundant[segment.id]
            else:
                category, score, reason = classify_segment(segment, slots)
            labels.append(QualityLabel(analysis_run_id=run.id, segment_id=segment.id, label=category, score=score, reason=reason))
        session.add_all(labels)
        session.flush()
        return labels

    @staticmethod
    def _persist_gaps(session: Session, run: AnalysisRun, document: Document, gap_types: list[str]) -> None:
        if session.scalar(select(Gap.id).where(Gap.analysis_run_id == run.id)) is None:
            session.add_all(Gap(analysis_run_id=run.id, document_id=document.id, gap_type=gap_type, severity=Severity.WARNING, description=gap_description(gap_type)) for gap_type in gap_types)

    @staticmethod
    def _metrics(document: Document, slots: list[SemanticSlot], relations: list[Relation], labels: list[QualityLabel]) -> QualityMetrics:
        token_counts = {category: sum(label.segment.token_count for label in labels if label.label == category) for category in QualityCategory}
        total = sum(segment.token_count for segment in document.segments)
        signal = signal_ratio(total_tokens=total, core_tokens=token_counts[QualityCategory.CORE_SIGNAL], supporting_tokens=token_counts[QualityCategory.SUPPORTING_SIGNAL])
        redundancy = redundancy_ratio(total_tokens=total, redundant_tokens=token_counts[QualityCategory.REDUNDANT])
        generic = generic_ratio(total_tokens=total, generic_tokens=token_counts[QualityCategory.GENERIC], rhetorical_tokens=token_counts[QualityCategory.RHETORICAL])
        evidence = evidence_coverage(slots, relations)
        completeness = decision_completeness(document.purpose.value if document.purpose else "EXPLAIN", slots)
        actionability = actionability_score(slots, relations)
        return QualityMetrics(signal_ratio=signal, redundancy_ratio=redundancy, generic_ratio=generic, evidence_coverage=evidence, decision_completeness=completeness, actionability_score=actionability, document_signal_score=document_signal_score(signal=signal, evidence=evidence, completeness=completeness, actionability=actionability, redundancy=redundancy, generic=generic))

    @staticmethod
    def _explanations(labels: list[QualityLabel], gaps: list[str]) -> list[str]:
        counts = {category: sum(label.label == category for label in labels) for category in QualityCategory}
        return [f"핵심 문장 {counts[QualityCategory.CORE_SIGNAL]}개", f"반복 문장 {counts[QualityCategory.REDUNDANT]}개", f"일반론 문장 {counts[QualityCategory.GENERIC] + counts[QualityCategory.RHETORICAL]}개", *[gap_description(gap) for gap in gaps]]
