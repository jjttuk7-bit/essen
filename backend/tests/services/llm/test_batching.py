"""One call carrying a whole document does not return inside any sane timeout.

Extraction time grows with the document, so a long report exceeded the socket timeout no
matter how high it was raised. Segments are sent in batches instead, concurrently, so each
call stays small and the wall clock is set by the slowest batch rather than by their sum.
"""

import json

from app.schemas.llm import AnalysisRequest, SourceSegment
from app.services.llm.openai_compatible import BATCH_SIZE, OpenAICompatibleLLMAdapter


class _Recorder:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def __call__(self, request, *_args, **_kwargs):
        payload = json.loads(request.data.decode("utf-8"))
        sent = json.loads(payload["messages"][1]["content"])
        ids = [segment["id"] for segment in sent["segments"]]
        self.batches.append(ids)
        slots = [
            {"slot": "FACT", "text": f"quote {segment_id}", "source_segment_id": segment_id,
             "source_span": None, "confidence": 0.9, "importance": 0.9}
            for segment_id in ids
        ]
        body = json.dumps({"choices": [{"message": {"content": json.dumps({"slots": slots})}}]})
        return _Response(body.encode("utf-8"))


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._body


def _adapter() -> OpenAICompatibleLLMAdapter:
    return OpenAICompatibleLLMAdapter(base_url="https://api.openai.com/v1", api_key="k", model="gpt-5-mini")


def _request(count: int) -> AnalysisRequest:
    return AnalysisRequest(segments=[SourceSegment(id=f"segment-{index}", text=f"본문 {index}입니다.") for index in range(count)])


def test_a_document_within_one_batch_makes_a_single_call(monkeypatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", recorder)

    _adapter().analyze(_request(BATCH_SIZE))

    assert len(recorder.batches) == 1


def test_a_longer_document_is_split_into_batches(monkeypatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", recorder)

    _adapter().analyze(_request(BATCH_SIZE * 3 + 1))

    assert len(recorder.batches) == 4


def test_every_segment_is_sent_exactly_once(monkeypatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", recorder)
    count = BATCH_SIZE * 2 + 3

    _adapter().analyze(_request(count))

    sent = [segment_id for batch in recorder.batches for segment_id in batch]
    assert sorted(sent) == sorted(f"segment-{index}" for index in range(count))
    assert len(sent) == len(set(sent))


def test_results_from_every_batch_are_merged(monkeypatch) -> None:
    recorder = _Recorder()
    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", recorder)
    count = BATCH_SIZE * 2 + 1

    analysis = _adapter().analyze(_request(count))

    assert {slot.source_segment_id for slot in analysis.slots} == {f"segment-{index}" for index in range(count)}


def test_merged_slots_follow_document_order(monkeypatch) -> None:
    """Batches finish out of order when run concurrently; the reader still needs source order."""
    recorder = _Recorder()
    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", recorder)
    count = BATCH_SIZE * 3

    analysis = _adapter().analyze(_request(count))

    assert [slot.source_segment_id for slot in analysis.slots] == [f"segment-{index}" for index in range(count)]


def test_a_failing_batch_does_not_lose_the_others(monkeypatch) -> None:
    """A long document should not be abandoned because one call was refused."""
    recorder = _Recorder()
    calls = {"n": 0}

    def flaky(request, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise TimeoutError("the read operation timed out")
        return recorder(request, *args, **kwargs)

    monkeypatch.setattr("app.services.llm.openai_compatible.urlopen", flaky)

    analysis = _adapter().analyze(_request(BATCH_SIZE * 3))

    assert analysis.slots
    assert len({slot.source_segment_id for slot in analysis.slots}) == BATCH_SIZE * 2
