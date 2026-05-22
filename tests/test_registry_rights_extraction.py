from src.document_ai.extract_fields import extract_fields
from src.document_ai.registry_parser import parse_money, parse_registry_text


SAMPLE_REGISTRY_RIGHTS_TEXT = """
등기사항전부증명서
갑구 소유권이전 접수일자 2026년 5월 1일
을구 근저당권 설정 채권최고액 금이억사천만원정
압류 등기 있음
가압류 등기 있음
신탁등기 수탁자 한국신탁
전세권 설정 있음
임차권등기명령 있음
소유권이전청구권가등기 있음
처분금지가처분 있음
"""


def test_parse_money_handles_registry_korean_units():
    assert parse_money("금이억오천만원정") == 250_000_000
    assert parse_money("2억 4천만원") == 240_000_000
    assert parse_money("₩250,000,000") == 250_000_000


def test_registry_parser_extracts_extended_rights_flags():
    result = parse_registry_text(SAMPLE_REGISTRY_RIGHTS_TEXT)

    assert result["registry_checked"] is True
    assert result["mortgage_flag"] is True
    assert result["mortgage_amount"] == 240_000_000
    assert result["seizure_flag"] is True
    assert result["provisional_seizure_flag"] is True
    assert result["trust_flag"] is True
    assert result["jeonse_right_flag"] is True
    assert result["leasehold_registration_flag"] is True
    assert result["ownership_transfer_recent_flag"] is True
    assert result["registry_warning_flag"] is True


def test_unknown_document_type_runs_registry_fallback():
    result = extract_fields("unknown", SAMPLE_REGISTRY_RIGHTS_TEXT)

    assert result["mortgage_flag"] is True
    assert result["mortgage_amount"] == 240_000_000
    assert result["seizure_flag"] is True
    assert result["provisional_seizure_flag"] is True
    assert result["trust_flag"] is True
    assert result["jeonse_right_flag"] is True
    assert result["registry_warning_flag"] is True


SAMPLE_REGISTRY_WITH_CANCELLED_ATTACHMENT = """
등기사항전부증명서 샘플
말소사항 포함 예
갑구
1 소유권보존 2017년 03월 20일
2 소유권이전 2020년 06월 10일
3 압류 2022년 11월 08일 체납처분에 의한 압류
4 3번 압류 말소 2023년 02월 14일 해제 말소
을구
1 근저당권설정 2020년 06월 10일 설정계약
채권최고액 금 420,000,000원
2 전세권설정 2024년 03월 04일 설정계약
전세금 금 360,000,000원
3 1번 근저당권 변경 2025년 01월 20일 변경계약 채권최고액 금 390,000,000원으로 변경
리스크 has_active_attachment false
리스크 has_active_mortgage true
"""


def test_registry_parser_does_not_clear_all_rights_when_one_attachment_is_cancelled():
    result = parse_registry_text(SAMPLE_REGISTRY_WITH_CANCELLED_ATTACHMENT)

    assert result["registry_checked"] is True
    assert result["mortgage_flag"] is True
    assert result["mortgage_amount"] == 390_000_000
    assert result["seizure_flag"] is False
    assert result["jeonse_right_flag"] is True
    assert result["ownership_transfer_recent_flag"] is True


def test_uploaded_sample_registry_pdf_text_keeps_active_mortgage_and_jeonse_right():
    sample_text = """
    등기사항전부증명서 샘플
    말소사항 포함 예
    소재지: 서울특별시 관악구 청룡동 875-12 청룡하이츠 제101동 제7층 제704호
    갑구
    1 소유권보존 2017년 03월 20일
    2 소유권이전 2020년 06월 10일 매매 소유자 이서연
    3 압류 2022년 11월 08일 체납처분에 의한 압류
    4 3번 압류 말소 2023년 02월 14일 해제 말소
    을구
    1 근저당권설정 2020년 06월 10일 설정계약
    채권최고액 금 420,000,000원
    2 전세권설정 2024년 03월 04일 설정계약
    전세금 금 360,000,000원
    3 1번 근저당권 변경 2025년 01월 20일 변경계약 채권최고액 금 390,000,000원으로 변경
    권리 mortgage_max_amount 390000000 변경 후 채권최고액
    권리 jeonse_amount 360000000 전세권 설정 전세금
    리스크 has_active_attachment false 말소되지 않은 압류 없음
    리스크 has_active_mortgage true 말소되지 않은 근저당권 있음
    압류 말소됨
    전세권 존재
    """
    result = parse_registry_text(sample_text)

    assert result["mortgage_flag"] is True
    assert result["mortgage_amount"] == 390_000_000
    assert result["seizure_flag"] is False
    assert result["jeonse_right_flag"] is True
    assert result["ownership_transfer_recent_flag"] is True
