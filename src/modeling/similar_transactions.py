from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RENT_PATH = ROOT / "data" / "processed" / "ganak_rent_clean.csv"
SALE_PATH = ROOT / "data" / "processed" / "ganak_sale_clean.csv"


def load_market_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    rent = pd.read_csv(RENT_PATH) if RENT_PATH.exists() else pd.DataFrame()
    sale = pd.read_csv(SALE_PATH) if SALE_PATH.exists() else pd.DataFrame()
    return rent, sale


def _filter_similar(df: pd.DataFrame, snapshot: dict[str, Any], transaction_type: str) -> pd.DataFrame:
    if df.empty:
        return df
    rows = df[df["transaction_type"].eq(transaction_type)].copy()
    housing_type = snapshot.get("housing_type")
    if housing_type:
        same_type = rows[rows["housing_type"].eq(housing_type)]
        if not same_type.empty:
            rows = same_type
    dong = snapshot.get("dong")
    address = snapshot.get("address", "")
    if dong:
        same_dong = rows[rows["dong"].eq(dong)]
        if not same_dong.empty:
            rows = same_dong
    elif "신림" in address:
        same_dong = rows[rows["dong"].str.contains("신림", na=False)]
        if not same_dong.empty:
            rows = same_dong
    area = float(snapshot.get("area_m2") or 0)
    if area:
        lower = area * 0.8
        upper = area * 1.2
        area_rows = rows[rows["area_m2"].between(lower, upper)]
        if not area_rows.empty:
            rows = area_rows
    return rows


def market_confidence(count: int) -> str:
    if count >= 10:
        return "높음"
    if count >= 3:
        return "보통"
    if count > 0:
        return "낮음"
    return "검토 제한"


def summarize_similar_transactions(snapshot: dict[str, Any]) -> dict[str, Any]:
    rent, sale = load_market_data()
    rent_similar = _filter_similar(rent, snapshot, "전세")
    sale_similar = _filter_similar(sale, snapshot, "매매")
    rent_fallback = rent if not rent.empty else pd.DataFrame()
    sale_fallback = sale if not sale.empty else pd.DataFrame()
    nearby_rent_median = int((rent_similar["deposit"] if not rent_similar.empty else rent_fallback.get("deposit", pd.Series([0]))).median() or 0)
    nearby_sale_median = int((sale_similar["price"] if not sale_similar.empty else sale_fallback.get("price", pd.Series([0]))).median() or 0)
    count = int(len(rent_similar) + len(sale_similar))
    return {
        "similar_transaction_count": count,
        "nearby_rent_median": nearby_rent_median,
        "nearby_sale_median": nearby_sale_median,
        "market_confidence": market_confidence(count),
        "rent_samples": rent_similar.head(10).to_dict("records"),
        "sale_samples": sale_similar.head(10).to_dict("records"),
    }
