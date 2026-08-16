"""Rule layer of core selection: what is essential, decided without a model.

Two things a model score cannot give us. Selection has to be reproducible for the same
document, and a reader owed an explanation needs a concrete one — "일반론 표현", "목차
항목" — where an importance number explains nothing. The model still judges what matters
in context; these rules decide what is even a candidate, and supply the wording of the
reason. Nothing here rewrites the source: rules only score passages the source already
contains.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# Korean marks its speech act in the ending, which makes directives and conclusions
# detectable without parsing the sentence.
DIRECTIVE = re.compile(r"(하라|해야\s|해야한다|하지\s*(말|않)|반드시|필수|지켜야|넘어가지\s*않는다|남긴다|확인한다|정한다|말라|마라)")
CONCLUSION = re.compile(r"(따라서|결국|요컨대|결론적으로|핵심은|즉,|정리하면)")
CAUSAL = re.compile(r"(때문에|로\s*인해|그래서|덕분에|탓에)")
WARNING = re.compile(r"(주의|위험|흔한\s*(실수|오류)|함정|착각|오인|왜곡|틀렸)")
# A figure counts as evidence only when it measures something. Bare numbers are version
# labels, section numbers and page numbers, which say nothing about the content.
FIGURES = re.compile(r"\d+\s*(%p|%|퍼센트|개월|주일|주|일|년|개월|명|건|회|배|위|점|원|만|억|시간|분|초|배수|퍼센트포인트)")
# An interrogative asks the reader something; it does not instruct them.
INTERROGATIVE = re.compile(r"(\?|는가|은가|ㄴ가|나요|까\??)\s*[”\"']?\s*$")
NUMBERED_HEADING = re.compile(r"^\d+(\.\d+)+\s+\S")
GENERIC = re.compile(r"(일반적으로|대체로|흔히|매우\s*중요|아주\s*중요|중요하다|다양한|여러\s*가지|바람직하|노력해야|최선을\s*다|in general|overall|best practice)")

TOC_MARKER = re.compile(r"(PART|CHAPTER)\s*\d+", re.IGNORECASE)
CHECKLIST_MARKER = re.compile(r"^\s*([①-⑳]|[·•▪◦]|[-*]\s|□|☐|✓|\d+[.)]\s)")
SENTENCE_END = re.compile(r"(다|요|까|음|함|\.|\?|!)\s*$")

SHAPE_BASE = {"BODY": 0.35, "CHECKLIST": 0.30, "TABLE": 0.05, "TOC": 0.02, "HEADING": 0.05}
SHAPE_REASON = {"TABLE": "표 조각", "TOC": "목차 항목", "HEADING": "제목 줄"}
TABLE_LINE_LENGTH = 24
TABLE_MIN_LINES = 4


class Shape(str, Enum):
    BODY = "BODY"
    CHECKLIST = "CHECKLIST"
    TABLE = "TABLE"
    TOC = "TOC"
    HEADING = "HEADING"


@dataclass(frozen=True)
class RuleScore:
    score: float
    reasons: tuple[str, ...]


def classify_shape(segment_text: str) -> Shape:
    """Read a segment's form from its layout, before any judgement about its content."""
    lines = [line.strip() for line in segment_text.split("\n") if line.strip()]
    if not lines:
        return Shape.BODY
    if len(TOC_MARKER.findall(segment_text)) >= 3:
        return Shape.TOC
    if lines[0].startswith("목차"):
        return Shape.TOC
    if CHECKLIST_MARKER.match(lines[0]):
        return Shape.CHECKLIST
    # A run of short lines that do not close as sentences is a table flattened by extraction.
    short_unfinished = [line for line in lines if len(line) <= TABLE_LINE_LENGTH and not SENTENCE_END.search(line)]
    if len(lines) >= TABLE_MIN_LINES and len(short_unfinished) >= len(lines) * 0.7:
        return Shape.TABLE
    return Shape.BODY


def score_passage(passage: str, shape: Shape) -> RuleScore:
    """Score one candidate passage, collecting the reasons behind the number."""
    text = " ".join(passage.split())
    reasons: list[str] = []
    score = SHAPE_BASE[shape.value]
    if reason := SHAPE_REASON.get(shape.value):
        reasons.append(reason)

    if not text:
        return RuleScore(0.0, ("내용 없음",))

    if NUMBERED_HEADING.match(text):
        return RuleScore(round(min(SHAPE_BASE[shape.value], 0.1), 4), ("절 제목",))

    is_question = bool(INTERROGATIVE.search(text))
    for pattern, weight, reason in (
        (DIRECTIVE, 0.0 if is_question else 0.30, "실행 지시"),
        (CONCLUSION, 0.20, "결론 표지"),
        (WARNING, 0.20, "주의·위험"),
        (CAUSAL, 0.10, "인과 설명"),
        (FIGURES, 0.15, "수치 근거"),
    ):
        if weight and pattern.search(text):
            score += weight
            reasons.append(reason)

    if GENERIC.search(text):
        score -= 0.25
        reasons.append("일반론 표현")

    if not reasons:
        reasons.append("본문 서술")
    return RuleScore(round(min(1.0, max(0.0, score)), 4), tuple(reasons))
