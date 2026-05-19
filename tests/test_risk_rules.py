from src.risk.market_indicators import calculate_market_indicators
from src.risk.risk_grade import grade_risk
from src.risk.risk_rules import calculate_risk_score


def test_high_risk_for_trust_and_high_ratio():
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

    assert score >= 75
    assert grade["grade"] == "고위험"
    assert any(signal["key"] == "trust" for signal in signals)
