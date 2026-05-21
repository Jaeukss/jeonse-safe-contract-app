from src.document_ai.basic_info_parser import extract_basic_info
from src.document_ai.pii_masking import has_unmasked_pii, mask_pii
from src.document_ai.registry_parser import parse_money, parse_registry_text


def test_parse_money_handles_korean_units_without_double_counting():
    assert parse_money("2억 4천만원") == 240_000_000
    assert parse_money("7천만원") == 70_000_000
    assert parse_money("246000000원") == 246_000_000


def test_registry_parser_extracts_core_flags():
    result = parse_registry_text("을구 근저당권 설정 채권최고액 1억 8000만원 신탁")

    assert result["mortgage_flag"] is True
    assert result["mortgage_amount"] == 180_000_000
    assert result["trust_flag"] is True


def test_registry_parser_respects_negative_flags():
    result = parse_registry_text("근저당권 없음 압류 없음 가압류 없음 신탁등기 없음 임차권등기 없음")

    assert result["mortgage_flag"] is False
    assert result["seizure_flag"] is False
    assert result["provisional_seizure_flag"] is False
    assert result["trust_flag"] is False
    assert result["leasehold_registration_flag"] is False


def test_basic_info_parser_extracts_contract_fields():
    result = extract_basic_info(
        "주소: 서울 강서구 화곡동 1027-8 해든빌라 402호\n"
        "주택유형: 연립다세대\n"
        "전세보증금: 2억 7천만원\n"
        "전용면적: 42.10㎡\n"
        "층: 4층\n"
        "사용승인일: 2016"
    )

    assert result["address"] == "서울 강서구 화곡동 1027-8 해든빌라 402호"
    assert result["housing_type"] == "연립다세대"
    assert result["deposit"] == 270_000_000
    assert result["area_m2"] == 42.1
    assert result["floor"] == 4
    assert result["built_year"] == 2016


def test_pii_masking_blocks_resident_number():
    masked, counts = mask_pii("임대인 900101-1234567 연락처 010-1234-5678")

    assert counts["resident_registration_number"] == 1
    assert counts["phone"] == 1
    assert not has_unmasked_pii(masked)
