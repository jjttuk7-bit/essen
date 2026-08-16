"""What this system may do with a document, decided by what kind of document it is.

The premise everything else rests on — that most of a document can go — is false for
documents whose every clause binds. Condensing a contract produces a plausible object
with an invisible hole in it, and the reader has no way to notice. Declining is the
honest outcome, and saying so is worth more to a user than a summary they cannot trust.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Handling(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUSED = "REFUSED"


@dataclass(frozen=True)
class Policy:
    handling: Handling
    reason: str


# Only named kinds are declined. Not recognising a document is not evidence against it,
# and refusing an ordinary document is a failure the user feels immediately.
REFUSED_KINDS = {
    "계약서": "계약서는 모든 조항이 효력을 갖습니다. 일부를 덜어낸 계약서는 빠진 조항이 보이지 않아 원본보다 위험합니다.",
    "법령·규정": "법령·규정은 조항 하나가 요건을 바꿉니다. 요약본으로는 무엇이 빠졌는지 확인할 방법이 없습니다.",
}


def policy_for(kind: str) -> Policy:
    if reason := REFUSED_KINDS.get(kind):
        return Policy(handling=Handling.REFUSED, reason=reason)
    return Policy(handling=Handling.SUPPORTED, reason="")
