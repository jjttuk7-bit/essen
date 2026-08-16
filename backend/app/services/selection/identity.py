"""What the document is, before what it says.

A reader handed a condensed document first has to work out what they are holding, and
that work comes before any of the content is usable. Everything here is either measured
from the document or quoted out of it — the kind is inferred from the mix of signals the
document already carries, and the purpose is the document's own sentence about itself.
Nothing is written on the document's behalf.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.services.renderer.outline import build_outline
from app.services.selection.rules import AGENDA, ATTRIBUTION, CONCLUSION, DIRECTIVE, FIGURES, INTERROGATIVE, SETTLED, Shape, classify_shape

SENTENCE = re.compile(r"(?<=다\.)\s+|(?<=[.!?])\s+|\n")
# A document that states its purpose does so about itself, by name.
SELF_REFERENCE = re.compile(r"(이|본)\s*(문서|플레이북|보고서|가이드|안내서|자료|글|계획서|제안서)")
PURPOSE_MARKER = re.compile(r"(목적은|위한|위해|채우려|다루려|설명하려|정리한|안내한|목표는|하고자)")
# Reading far enough in to find a preamble, but not so far that a body sentence qualifies.
PURPOSE_LOOKAHEAD = 6

# Measured against real documents rather than guessed. A guide can be organized around
# questions and still be a guide, so a questionnaire has to be almost nothing but
# questions; a guide only needs instructions at a steady rate.
QUESTIONNAIRE_SHARE = 0.4
QUESTIONNAIRE_DIRECTIVE_CEILING = 0.05
GUIDE_DIRECTIVE_SHARE = 0.08
REPORT_SHARE = 0.12
# Minutes announce themselves in their opening block, then number their agenda. Either
# alone is weak — a report can list attendees, a guide can number sections — so both count.
MINUTES_HEADER = re.compile(r"(참석|참가자|배석|일시\s*[:：]|장소\s*[:：]|회의록|회의\s*결과)")
MINUTES_MARKS = 2
# Binding documents are numbered by article and carry the machinery of obligation. A
# report can mention any one of these, so several marks are required before declining.
ARTICLE = re.compile(r"^제\s*\d+\s*조")
CONTRACT_MARKS = (
    re.compile(r"이하\s*[\"“'‘]?[갑을][\"”'’]?|[\"“'‘]?갑[\"”'’]?\s*(과|와|은|는|이|의)\s"),
    re.compile(r"(계약을\s*체결|본\s*계약|이\s*계약서|계약당사자)"),
    re.compile(r"(서명\s*날인|기명날인|각\s*1부씩\s*보관)"),
    re.compile(r"(손해배상|위약금|계약을?\s*해지|계약해제)"),
)
STATUTE_MARKS = (
    re.compile(r"^\s*부칙", re.MULTILINE),
    re.compile(r"(법률\s*제\s*\d+\s*호|대통령령|총리령|부령|시행령|시행규칙)"),
    re.compile(r"(이\s*법은|이\s*영은|공포\s*후)"),
    re.compile(r"(하여야\s*한다|정하는\s*바에\s*따른다)"),
)
# Enough articles that the document is built out of them, not merely citing one.
BINDING_ARTICLES = 3
BINDING_MARKS = 3
# A continued thought after a dash or an opening quote belongs to the sentence before it.
CONTINUATION = re.compile("^[—–\\-\"“‘']")


@dataclass(frozen=True)
class DocumentIdentity:
    kind: str
    section_count: int
    segment_count: int
    character_count: int
    purpose: str | None


def _sentences(text: str) -> list[str]:
    return [" ".join(part.split()) for part in SENTENCE.split(text) if len(part.strip()) >= 10]


def _binding_kind(segments: Sequence[object]) -> str | None:
    """Name a contract or a statute, or nothing.

    Both are built from numbered articles, so the article count is the gate and the
    surrounding machinery decides which. Several marks are required because a report that
    discusses a contract uses the same words without being one.
    """
    joined = "\n".join(getattr(segment, "text", "") for segment in segments)
    lines = [line.strip() for line in joined.split("\n") if line.strip()]
    if sum(1 for line in lines if ARTICLE.match(line)) < BINDING_ARTICLES:
        return None
    contract = sum(1 for pattern in CONTRACT_MARKS if pattern.search(joined))
    statute = sum(1 for pattern in STATUTE_MARKS if pattern.search(joined))
    if contract >= BINDING_MARKS and contract >= statute:
        return "계약서"
    if statute >= BINDING_MARKS:
        return "법령·규정"
    return None


def _looks_like_minutes(segments: Sequence[object]) -> bool:
    """Header block, numbered agenda, attributed speech, recorded decisions — two of four."""
    joined = "\n".join(getattr(segment, "text", "") for segment in segments)
    lines = [line.strip() for line in joined.split("\n") if line.strip()]
    marks = sum([
        bool(MINUTES_HEADER.search(joined)),
        any(AGENDA.match(line) for line in lines),
        any(ATTRIBUTION.match(line) for line in lines),
        bool(SETTLED.search(joined)),
    ])
    return marks >= MINUTES_MARKS


def _kind(sentences: Sequence[str], minutes: bool = False) -> str:
    """Name the document from the mix of speech acts it is made of."""
    if not sentences:
        return "일반 문서"
    total = len(sentences)
    directives = sum(1 for line in sentences if DIRECTIVE.search(line))
    findings = sum(1 for line in sentences if FIGURES.search(line))
    questions = sum(1 for line in sentences if INTERROGATIVE.search(line))
    concluding = sum(1 for line in sentences if CONCLUSION.search(line))

    if minutes:
        return "회의록"
    if questions / total >= QUESTIONNAIRE_SHARE and directives / total < QUESTIONNAIRE_DIRECTIVE_CEILING:
        return "질문지"
    if directives / total >= GUIDE_DIRECTIVE_SHARE:
        return "절차 안내서"
    if (findings + concluding) / total >= REPORT_SHARE:
        return "분석 보고서"
    return "일반 문서"


def _purpose(segments: Sequence[object]) -> str | None:
    """Quote the document's own sentence about what it is for, if it has one."""
    for segment in segments[:PURPOSE_LOOKAHEAD]:
        sentences = _sentences(getattr(segment, "text", ""))
        for index, sentence in enumerate(sentences):
            if not (SELF_REFERENCE.search(sentence) and PURPOSE_MARKER.search(sentence)):
                continue
            following = sentences[index + 1] if index + 1 < len(sentences) else ""
            # Still verbatim: the two sentences are contiguous in the source.
            return f"{sentence} {following}".strip() if CONTINUATION.match(following) else sentence
    return None


def identify_document(segments: Sequence[object]) -> DocumentIdentity:
    ordered = sorted(segments, key=lambda segment: getattr(segment, "order_index", 0))
    # Tables and contents pages carry incidental question marks and instruction endings,
    # so they are not evidence of anything. Checklists are: a numbered run of questions is
    # exactly what a questionnaire is made of.
    sentences = [
        line for segment in ordered
        if classify_shape(getattr(segment, "text", "")) not in (Shape.TOC, Shape.TABLE)
        for line in _sentences(getattr(segment, "text", ""))
    ]
    outline = build_outline(ordered)
    return DocumentIdentity(
        kind=_binding_kind(ordered) or _kind(sentences, _looks_like_minutes(ordered)),
        section_count=len(outline.ordered_headings),
        segment_count=len(ordered),
        character_count=sum(len(getattr(segment, "text", "")) for segment in ordered),
        purpose=_purpose(ordered),
    )
