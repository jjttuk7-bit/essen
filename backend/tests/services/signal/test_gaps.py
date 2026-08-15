from app.services.signal.gaps import find_gaps


def test_decide_document_without_evidence_reports_gap() -> None:
    assert "MISSING_EVIDENCE" in find_gaps("DECIDE", slots=[])


def test_decide_document_without_trade_off_reports_gap() -> None:
    from app.models.analysis import SemanticSlot, SlotType

    slots = [SemanticSlot(id="problem", analysis_run_id="run", source_segment_id="seg", slot_type=SlotType.PROBLEM, normalized_text="Problem", confidence=1, importance=1)]
    assert "MISSING_TRADE_OFF" in find_gaps("DECIDE", slots)

def test_decide_document_without_trade_off_reports_gap() -> None:
    from app.models.analysis import SemanticSlot, SlotType

    slots = [SemanticSlot(id="problem", analysis_run_id="run", source_segment_id="seg", slot_type=SlotType.PROBLEM, normalized_text="Problem", confidence=1, importance=1)]
    assert "MISSING_TRADE_OFF" in find_gaps("DECIDE", slots)