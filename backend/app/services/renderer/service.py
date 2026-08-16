from collections.abc import Sequence

from app.services.renderer.action_decision import render_action_decision_sheet
from app.services.renderer.base import RenderedDocument, RenderedSection, UnsupportedClaimError
from app.services.renderer.clean import render_clean_version
from app.services.renderer.executive import render_executive_summary


class RendererService:
    _renderers = {"clean_version": render_clean_version, "executive_summary": render_executive_summary, "action_decision_sheet": render_action_decision_sheet}

    def render(self, output_type: str, slots: Sequence[object], quality_labels: Sequence[object] = (), audience: str | None = None, max_words: int | None = None) -> RenderedDocument:
        try:
            renderer = self._renderers[output_type]
        except KeyError as error:
            raise ValueError(f"Unsupported output type: {output_type}") from error
        output = renderer(slots, quality_labels) if output_type == "clean_version" else renderer(slots)
        self.validate_sections(output.sections, slots)
        return self._limit_words(self._apply_audience(output, audience), max_words)

    def render_all(self, slots: Sequence[object], quality_labels: Sequence[object] = (), audience: str | None = None, max_words: int | None = None) -> list[RenderedDocument]:
        return [self.render(output_type, slots, quality_labels, audience, max_words) for output_type in self._renderers]

    def validate_sections(self, sections: Sequence[RenderedSection], slots: Sequence[object]) -> None:
        slot_segment_ids = {getattr(slot, "id"): getattr(slot, "source_segment_id") for slot in slots}
        for section in sections:
            if not section.source_slot_ids:
                raise UnsupportedClaimError("Each rendered section needs a source semantic slot")
            if len(section.source_slot_ids) != len(section.source_segment_ids):
                raise UnsupportedClaimError("Rendered section must retain a source segment for every semantic slot")
            for slot_id, segment_id in zip(section.source_slot_ids, section.source_segment_ids, strict=True):
                if slot_segment_ids.get(slot_id) != segment_id:
                    raise UnsupportedClaimError("Rendered section cites an invalid source segment")

    @staticmethod
    def _apply_audience(output: RenderedDocument, audience: str | None) -> RenderedDocument:
        prefix = audience.strip() if audience else ""
        if not prefix:
            return output
        return RenderedDocument(output.output_type, [
            RenderedSection(f"{prefix}: {section.heading}", section.text, section.source_slot_ids, section.source_segment_ids)
            for section in output.sections
        ])

    @staticmethod
    def _limit_words(output: RenderedDocument, max_words: int | None) -> RenderedDocument:
        if max_words is None:
            return output
        remaining = max_words
        sections: list[RenderedSection] = []
        for section in output.sections:
            words = section.text.split()
            if remaining <= 0:
                break
            sections.append(RenderedSection(section.heading, " ".join(words[:remaining]), section.source_slot_ids, section.source_segment_ids))
            remaining -= len(words)
        return RenderedDocument(output.output_type, sections)
