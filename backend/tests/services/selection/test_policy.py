"""Which documents this system may condense, and which it must decline.

The product's premise is that most of a document can go. For a contract or a statute that
premise is false: every clause binds, and a version with 70% removed is a dangerous
object. The failure would also be silent — a plausible summary, with the missing clause
invisible — so these are declined rather than handled badly.

Declining wrongly is its own harm, so each detector needs several marks before it fires.
"""

import pytest

from types import SimpleNamespace

from app.services.selection.identity import identify_document
from app.services.selection.policy import Handling, policy_for

CONTRACT = """소프트웨어 개발 용역 계약서

주식회사 가나(이하 "갑"이라 한다)와 주식회사 다라(이하 "을"이라 한다)는 다음과 같이 계약을 체결한다.

제1조 (목적) 본 계약은 갑이 을에게 위탁하는 소프트웨어 개발 용역의 조건을 정함을 목적으로 한다.

제2조 (계약금액) 계약금액은 금 오천만원(₩50,000,000)으로 한다.

제3조 (기간) 계약기간은 2026년 4월 1일부터 2026년 9월 30일까지로 한다.

제4조 (손해배상) 을이 납기를 지연한 경우 지연일수 1일당 계약금액의 1000분의 3을 배상한다.

제5조 (해지) 갑은 을이 본 계약을 위반한 경우 최고 없이 계약을 해지할 수 있다.

본 계약을 증명하기 위하여 계약서 2부를 작성하여 각각 서명 날인 후 1부씩 보관한다."""

STATUTE = """공공데이터의 제공 및 이용 활성화에 관한 법률

제1조(목적) 이 법은 공공기관이 보유·관리하는 데이터의 제공에 관한 사항을 규정함을 목적으로 한다.

제2조(정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.

제3조(적용 범위) 공공데이터의 제공에 관하여는 다른 법률에 특별한 규정이 있는 경우를 제외하고는 이 법으로 정하는 바에 따른다.

제4조(국가의 책무) 국가는 공공데이터의 이용 활성화를 위하여 필요한 시책을 마련하여야 한다.

부칙 <법률 제12345호, 2026. 1. 1.> 이 법은 공포 후 6개월이 경과한 날부터 시행한다."""

REPORT_MENTIONING_A_CONTRACT = """2026년 상반기 위탁사업 점검 보고

외부 위탁 계약 3건을 점검했다. 계약금액 합계는 1억 2천만원이다.
A업체는 납기를 2주 지연했으나 손해배상 조항을 적용하지 않았다.
따라서 계약 관리 절차를 재정비할 필요가 있다."""

MINUTES_ABOUT_A_CONTRACT = """2026년 3월 12일 14:00
참석: 김민수, 이서연

안건 1. 외주 계약 갱신
김민수: 계약 만료가 다음 달입니다. 갱신 여부를 정해야 합니다.
이서연: 단가를 조정하면 갱신하는 게 낫습니다.
갱신하기로 결정했다. 담당: 김민수, 기한: 3월 25일까지 계약서 초안 회신."""


def _segments(text: str) -> list[SimpleNamespace]:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    return [SimpleNamespace(id=f"segment-{index}", order_index=index, text=block) for index, block in enumerate(blocks)]


class TestRecognisingDocumentsWeMustNotCondense:
    def test_a_contract_is_recognized(self) -> None:
        assert identify_document(_segments(CONTRACT)).kind == "계약서"

    def test_a_statute_is_recognized(self) -> None:
        assert identify_document(_segments(STATUTE)).kind == "법령·규정"


class TestNotOverreaching:
    """Declining a normal document is its own failure, and a worse one to the user."""

    def test_a_report_that_discusses_contracts_is_not_a_contract(self) -> None:
        assert identify_document(_segments(REPORT_MENTIONING_A_CONTRACT)).kind != "계약서"

    def test_minutes_about_a_contract_renewal_are_still_minutes(self) -> None:
        assert identify_document(_segments(MINUTES_ABOUT_A_CONTRACT)).kind == "회의록"

    @pytest.mark.parametrize("kind", ["회의록", "절차 안내서", "분석 보고서", "질문지", "일반 문서"])
    def test_ordinary_kinds_are_handled(self, kind: str) -> None:
        assert policy_for(kind).handling is Handling.SUPPORTED


class TestThePolicy:
    @pytest.mark.parametrize("kind", ["계약서", "법령·규정"])
    def test_binding_documents_are_declined(self, kind: str) -> None:
        assert policy_for(kind).handling is Handling.REFUSED

    @pytest.mark.parametrize("kind", ["계약서", "법령·규정"])
    def test_a_declined_document_is_told_why(self, kind: str) -> None:
        reason = policy_for(kind).reason

        assert reason
        assert kind in reason

    def test_an_unknown_kind_is_handled_rather_than_declined(self) -> None:
        """Silence about a kind is not evidence against it; only named kinds are declined."""
        assert policy_for("처음 보는 종류").handling is Handling.SUPPORTED

    def test_a_supported_kind_needs_no_reason(self) -> None:
        assert policy_for("회의록").reason == ""
