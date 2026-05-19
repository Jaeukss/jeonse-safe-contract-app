from __future__ import annotations

from typing import Any


def calculate_market_indicators(snapshot: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    deposit = int(snapshot.get("deposit") or 0)
    rent_price = max(int(prediction.get("predicted_rent_price") or 0), 1)
    sale_price = max(int(prediction.get("predicted_sale_price") or 0), 1)
    similar_count = int(prediction.get("similar_transaction_count") or 0)
    jeonse_ratio = deposit / sale_price * 100
    rent_gap_rate = deposit / rent_price * 100
    score = 0
    if jeonse_ratio >= 90:
        score += 30
    elif jeonse_ratio >= 80:
        score += 15
    if rent_gap_rate >= 130:
        score += 30
    elif rent_gap_rate >= 115:
        score += 20
    if similar_count == 0:
        score += 20
    elif similar_count <= 2:
        score += 10
    return {
        "jeonse_ratio": round(jeonse_ratio, 1),
        "rent_gap_rate": round(rent_gap_rate, 1),
        "similar_transaction_count": similar_count,
        "market_confidence": prediction.get("market_confidence", "검토 제한"),
        "market_risk_score": score,
        "market_insufficient_flag": similar_count == 0,
    }
