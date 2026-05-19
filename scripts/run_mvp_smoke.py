from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.graph import run_agent_workflow
from src.document_ai.pii_masking import has_unmasked_pii, mask_pii
from src.document_ai.registry_parser import parse_registry_text
from src.input_layer import snapshot as snapshot_module
from src.input_layer.detect_conflict import detect_conflicts
from src.risk.market_indicators import calculate_market_indicators
from src.risk.risk_grade import grade_risk
from src.risk.risk_rules import calculate_risk_score


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    registry = parse_registry_text("을구 근저당권 설정 채권최고액 1억 8000만원 신탁")
    assert_true(registry["mortgage_flag"] is True, "mortgage flag should be true")
    assert_true(registry["mortgage_amount"] == 180_000_000, "mortgage amount should be parsed")
    assert_true(registry["trust_flag"] is True, "trust flag should be true")

    masked, counts = mask_pii("임대인 900101-1234567 연락처 010-1234-5678")
    assert_true(counts["resident_registration_number"] == 1, "resident number should be masked")
    assert_true(not has_unmasked_pii(masked), "masked text should not contain PII")

    conflicts = detect_conflicts(
        {
            "mortgage_flag": [
                {"value": True, "source": "registry_ocr", "confidence": 0.8},
                {"value": False, "source": "user_checklist", "confidence": 0.75},
            ]
        }
    )
    assert_true(conflicts and conflicts[0]["field"] == "mortgage_flag", "conflict should be detected")

    snapshot = {
        "address": "서울시 관악구 신림동",
        "housing_type": "다가구",
        "deposit": 650_000_000,
        "area_m2": 27.1,
        "registry_checked": True,
        "building_register_checked": True,
        "broker_explanation_checked": True,
        "trust_flag": True,
        "senior_deposit_checked": False,
    }
    prediction = {
        "predicted_rent_price": 500_000_000,
        "predicted_sale_price": 700_000_000,
        "similar_transaction_count": 2,
        "market_confidence": "낮음",
    }
    market = {**prediction, **calculate_market_indicators(snapshot, prediction)}
    score, signals, blockers = calculate_risk_score(snapshot, market)
    grade = grade_risk(score, snapshot, blockers)
    assert_true(score >= 75, "high risk score expected")
    assert_true(grade["grade"] == "고위험", "trust should force high risk")
    assert_true(any(signal["key"] == "trust" for signal in signals), "trust signal expected")

    records = [
        {
            "input_id": "RAW-1",
            "session_id": "S-SMOKE",
            "source": "user_input",
            "data": {
                "address": "서울시 관악구 신림동",
                "district": "관악구",
                "dong": "신림동",
                "housing_type": "다가구",
                "deposit": 135_000_000,
                "area_m2": 27.1,
                "floor": 2,
            },
        },
        {
            "input_id": "RAW-2",
            "session_id": "S-SMOKE",
            "source": "user_checklist",
            "data": {
                "registry_checked": True,
                "building_register_checked": True,
                "broker_explanation_checked": False,
                "mortgage_flag": False,
                "seizure_flag": False,
                "trust_flag": None,
                "senior_deposit_checked": False,
            },
        },
    ]
    with tempfile.TemporaryDirectory() as temp_dir:
        snapshot_module.SNAPSHOT_DIR = Path(temp_dir)
        result = run_agent_workflow({"session_id": "S-SMOKE", "records": records})
    assert_true("전세계약 위험진단 리포트" in result["report_markdown"], "report should be generated")
    print("MVP smoke tests passed")


if __name__ == "__main__":
    main()
