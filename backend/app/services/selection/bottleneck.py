"""Detect what in a document costs its reader time.

Length alone is not the problem. What costs attention is structure the reader must read
before discovering it is not content, the same point made again, sentences that commit to
nothing, a decision buried inside a wall of prose, and questions left standing. Naming
these turns a bare compression ratio into a reason the reader can check.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from app.services.selection.rules import GENERIC, INTERROGATIVE, Shape, classify_shape, score_passage

SENTENCE = re.compile(r"(?<=다\.)\s+|(?<=[.!?])\s+|\n")
WORD = re.compile(r"[0-9A-Za-z가-힣]+")

# Restating a point costs the reader a comparison, so near-identical wording counts.
REPETITION_SIMILARITY = 0.7
# Long enough that a reader skimming will miss a single decisive sentence inside it.
BURIED_LENGTH = 400
BURIED_CORE_SHARE = 0.25
# One open question is a prompt; a run of them is a document that decided nothing.
UNRESOLVED_RUN = 3
CORE_SCORE = 0.55


class Bottleneck(str, Enum):
    STRUCTURE_NOISE = "STRUCTURE_NOISE"
    REPETITION = "REPETITION"
    GENERALITY = "GENERALITY"
    BURIED_CORE = "BURIED_CORE"
    UNRESOLVED = "UNRESOLVED"


LABELS = {
    Bottleneck.STRUCTURE_NOISE: "구조 노이즈",
    Bottleneck.REPETITION: "반복",
    Bottleneck.GENERALITY: "일반론",
    Bottleneck.BURIED_CORE: "매몰된 핵심",
    Bottleneck.UNRESOLVED: "미해결 질문",
}


@dataclass(frozen=True)
class BottleneckFinding:
    kind: Bottleneck
    share: float
    detail: str
    segment_ids: tuple[str, ...]

    @property
    def label(self) -> str:
        return LABELS[self.kind]


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.casefold()))


def _similar(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _sentences(text: str) -> list[str]:
    return [" ".join(part.split()) for part in SENTENCE.split(text) if len(part.strip()) >= 10]


def _structure_noise(segments: Sequence[object]) -> tuple[list[str], str]:
    noisy = [getattr(segment, "id") for segment in segments if classify_shape(getattr(segment, "text")) in (Shape.TOC, Shape.TABLE)]
    return noisy, f"목차·표 조각 {len(noisy)}개 문단은 읽고 나서야 본문이 아님을 알게 됩니다"


def _repetition(segments: Sequence[object]) -> tuple[list[str], str]:
    seen: list[set[str]] = []
    repeats: list[str] = []
    for segment in segments:
        words = _words(getattr(segment, "text"))
        if any(_similar(words, earlier) >= REPETITION_SIMILARITY for earlier in seen):
            repeats.append(getattr(segment, "id"))
        else:
            seen.append(words)
    return repeats, f"같은 내용이 {len(repeats)}번 다시 나와 앞 내용과 대조하게 됩니다"


def _generality(segments: Sequence[object]) -> tuple[list[str], str]:
    generic = [getattr(segment, "id") for segment in segments if GENERIC.search(getattr(segment, "text"))]
    return generic, f"{len(generic)}개 문단이 일반론이라 읽어도 남는 정보가 없습니다"


def _buried_core(segments: Sequence[object]) -> tuple[list[str], str]:
    buried: list[str] = []
    for segment in segments:
        text = getattr(segment, "text")
        if len(text) < BURIED_LENGTH:
            continue
        sentences = _sentences(text)
        if not sentences:
            continue
        shape = classify_shape(text)
        core = [line for line in sentences if score_passage(line, shape).score >= CORE_SCORE]
        if core and len(core) / len(sentences) <= BURIED_CORE_SHARE:
            buried.append(getattr(segment, "id"))
    return buried, f"{len(buried)}개 긴 문단은 핵심이 본문 속에 묻혀 훑어서는 보이지 않습니다"


def _unresolved(segments: Sequence[object]) -> tuple[list[str], str]:
    asking = [getattr(segment, "id") for segment in segments if INTERROGATIVE.search(" ".join(getattr(segment, "text").split()))]
    if len(asking) < UNRESOLVED_RUN:
        return [], ""
    return asking, f"답이 붙지 않은 질문이 {len(asking)}개라 판단을 내릴 수 없습니다"


DETECTORS = (
    (Bottleneck.STRUCTURE_NOISE, _structure_noise),
    (Bottleneck.REPETITION, _repetition),
    (Bottleneck.GENERALITY, _generality),
    (Bottleneck.BURIED_CORE, _buried_core),
    (Bottleneck.UNRESOLVED, _unresolved),
)


def detect_bottlenecks(segments: Sequence[object]) -> list[BottleneckFinding]:
    """Report each bottleneck this document carries, costliest first."""
    ordered = sorted(segments, key=lambda segment: getattr(segment, "order_index", 0))
    if not ordered:
        return []

    findings = []
    for kind, detect in DETECTORS:
        segment_ids, detail = detect(ordered)
        if segment_ids:
            findings.append(BottleneckFinding(kind=kind, share=round(len(segment_ids) / len(ordered), 4), detail=detail, segment_ids=tuple(segment_ids)))
    return sorted(findings, key=lambda finding: -finding.share)
