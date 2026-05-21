from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_bootstrap import ensure_data_available

from .similar_transactions import summarize_similar_transactions


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_PRICE_PATH = ROOT / "data" / "processed" / "gwanak_gangseo_official_house_price_latest.csv"


@lru_cache(maxsize=1)
def _load_official_prices() -> pd.DataFrame:
    ensure_data_available()
    if not OFFICIAL_PRICE_PATH.exists():
        return pd.DataFrame()
    columns = [
        "building_register_pk",
        "legal_dong_code",
        "bun",
        "ji",
        "lot_address",
        "road_address",
        "building_name",
        "official_house_price",
        "price_base_date",
    ]
    return pd.read_csv(OFFICIAL_PRICE_PATH, usecols=lambda col: col in columns, dtype=str, low_memory=False)


def _median_price(rows: pd.DataFrame) -> int:
    if rows.empty:
        return 0
    prices = pd.to_numeric(rows["official_house_price"], errors="coerce").dropna()
    return int(prices.median() or 0)


def _code(value: Any, width: int | None = None) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(width) if width else text


def _official_house_price(snapshot: dict[str, Any]) -> int:
    prices = _load_official_prices()
    if prices.empty:
        return 0

    pk = snapshot.get("building_register_pk")
    if pk:
        matched = prices[prices["building_register_pk"].astype(str).eq(str(pk))]
        if not matched.empty:
            return _median_price(matched)

    legal_dong_code = _code(snapshot.get("legal_dong_code"))
    bun = _code(snapshot.get("bun"), 4)
    ji = _code(snapshot.get("ji"), 4)
    if legal_dong_code and bun and ji and {"legal_dong_code", "bun", "ji"}.issubset(prices.columns):
        matched = prices[
            prices["legal_dong_code"].map(_code).eq(legal_dong_code)
            & prices["bun"].map(lambda value: _code(value, 4)).eq(bun)
            & prices["ji"].map(lambda value: _code(value, 4)).eq(ji)
        ]
        if not matched.empty:
            return _median_price(matched)

    public_address = str(snapshot.get("public_building_address") or "")
    if public_address and "lot_address" in prices:
        matched = prices[prices["lot_address"].astype(str).eq(public_address)]
        if not matched.empty:
            return _median_price(matched)
    return 0


def predict_prices(snapshot: dict[str, Any]) -> dict[str, Any]:
    market = summarize_similar_transactions(snapshot)
    rent_price = market["nearby_rent_median"]
    sale_price = market["nearby_sale_median"]
    official_price = _official_house_price(snapshot)
    note = "유사 거래 중앙값 사용"
    if not rent_price:
        rent_price = int(snapshot.get("deposit") or 0)
        note = "전세 유사 거래 부족, 사용자 보증금 fallback"
    if not sale_price:
        if official_price:
            sale_price = official_price
            note = "매매 유사 거래 부족, 주택가격 보조값 fallback"
        else:
            deposit = int(snapshot.get("deposit") or 0)
            sale_price = int(deposit / 0.75) if deposit else 0
            note = "매매 유사 거래 부족, 전세가율 75% 역산 fallback"
    return {
        **market,
        "predicted_rent_price": rent_price,
        "predicted_sale_price": sale_price,
        "official_house_price": official_price,
        "model_note": note,
    }
