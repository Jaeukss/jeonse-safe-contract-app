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
