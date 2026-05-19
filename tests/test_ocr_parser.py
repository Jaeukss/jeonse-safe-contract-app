from src.document_ai.registry_parser import parse_registry_text
from src.document_ai.pii_masking import has_unmasked_pii, mask_pii


def test_registry_parser_extracts_core_flags():
    result = parse_registry_text("을구 근저당권 설정 채권최고액 1억 8000만원 신탁")

    assert result["mortgage_flag"] is True
    assert result["mortgage_amount"] == 180_000_000
    assert result["trust_flag"] is True


def test_pii_masking_blocks_resident_number():
    masked, counts = mask_pii("임대인 900101-1234567 연락처 010-1234-5678")

    assert counts["resident_registration_number"] == 1
    assert counts["phone"] == 1
    assert not has_unmasked_pii(masked)
