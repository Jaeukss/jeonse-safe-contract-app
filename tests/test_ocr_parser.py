from src.document_ai.basic_info_parser import extract_basic_info
from src.document_ai.extract_fields import extract_fields
from src.document_ai.llm_json_extractor import _parse_llm_json
from src.document_ai.pii_masking import has_unmasked_pii, mask_pii
from src.document_ai.registry_parser import parse_money, parse_registry_text


def test_parse_money_handles_korean_units_without_double_counting():
    assert parse_money("2억 4천만원") == 240_000_000
    assert parse_money("7천만원") == 70_000_000
    assert parse_money("246000000원") == 246_000_000
    assert parse_money("금이억오천만원정") == 250_000_000
    assert parse_money("천오백만") == 15_000_000
    assert parse_money("₩250,000,000") == 250_000_000
    assert parse_money("1억 2,000") == 120_000_000


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


def test_basic_info_parser_extracts_all_basic_input_fields_from_common_labels():
    result = extract_basic_info(
        "임대차계약서\n"
        "임대차목적물 소재지: 서울특별시 강서구 화곡동 999-1 테스트빌라 201호\n"
        "주택 유형: 연립주택\n"
        "임대차보증금: 금 1억 5천만원\n"
        "월차임: 30만원\n"
        "전유면적: 33.50㎡\n"
        "해당층: 제2층\n"
        "사용승인일: 2010.05.01\n"
        "계약일: 2026.05.21"
    )

    assert result["address"] == "서울특별시 강서구 화곡동 999-1 테스트빌라 201호"
    assert result["housing_type"] == "연립다세대"
    assert result["contract_stage"] == "계약 당일"
    assert result["deposit"] == 150_000_000
    assert result["monthly_rent"] == 300_000
    assert result["area_m2"] == 33.5
    assert result["floor"] == 2
    assert result["built_year"] == 2010


def test_basic_info_parser_restores_fragmented_address_and_hangul_money():
    result = extract_basic_info(
        "부동산의 표시\n"
        "서울특별\n"
        "시 관악\n"
        "구 봉천\n"
        "동 123-4 해든빌라 501호\n"
        "보증금 금이억오천만원정\n"
        "월세 없음\n"
    )

    assert result["address"].startswith("서울특별시 관악구 봉천동 123-4")
    assert result["room"] == "501호"
    assert result["deposit"] == 250_000_000
    assert result["contract_type"] == "전세"


def test_basic_info_parser_flags_impossible_floor_without_prefill():
    result = extract_basic_info("서울 강서구 화곡동 1027-8 8층 501호 OCR 오류 850층 보증금 2억")

    assert "floor" not in result
    assert result["extraction_outlier_flag"] is True
    assert result["manual_review_required"] is True
    assert any("조건 A" in reason for reason in result["extraction_outlier_reasons"])


def test_llm_json_parser_accepts_nested_validation_schema():
    result = _parse_llm_json(
        """
        {
          "address": {
            "city": "서울특별시",
            "borough": "강서구",
            "dong": "화곡동",
            "building_name": "해든빌라",
            "floor": 850,
            "room": "501호"
          },
          "contract": {
            "deposit": 270000000,
            "monthly_rent": 0,
            "contract_type": "전세"
          },
          "validation_status": {
            "is_outlier": true,
            "outlier_reason": "조건 A: 층수 오류"
          }
        }
        """
    )

    assert result["address"] == "서울특별시 강서구 화곡동 해든빌라"
    assert result["deposit"] == 270_000_000
    assert result["room"] == "501호"
    assert result["extraction_outlier_flag"] is True
    assert result["extraction_outlier_reasons"] == ["조건 A: 층수 오류"]


def test_pii_masking_blocks_resident_number():
    masked, counts = mask_pii("임대인 900101-1234567 연락처 010-1234-5678")

    assert counts["resident_registration_number"] == 1
    assert counts["phone"] == 1
    assert not has_unmasked_pii(masked)


def test_extract_fields_runs_without_llm_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = extract_fields("explanation", "주소: 서울 강서구 화곡동 1-1\n보증금: 1억\n월차임: 20만원")

    assert result["address"] == "서울 강서구 화곡동 1-1"
    assert result["deposit"] == 100_000_000
    assert result["monthly_rent"] == 200_000
