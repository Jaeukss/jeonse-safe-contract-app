from __future__ import annotations

from typing import Any

from .similar_transactions import summarize_similar_transactions


def predict_prices(snapshot: dict[str, Any]) -> dict[str, Any]:
    market = summarize_similar_transactions(snapshot)
    rent_price = market["nearby_rent_median"]
    sale_price = market["nearby_sale_median"]
    note = "유사 거래 중앙값 사용"
    if not rent_price:
        rent_price = int(snapshot.get("deposit") or 0)
        note = "전세 유사 거래 부족, 사용자 보증금 fallback"
    if not sale_price:
        deposit = int(snapshot.get("deposit") or 0)
        sale_price = int(deposit / 0.75) if deposit else 0
        note = "매매 유사 거래 부족, 전세가율 75% 역산 fallback"
    return {
        **market,
        "predicted_rent_price": rent_price,
        "predicted_sale_price": sale_price,
        "model_note": note,
    }
