from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .address import NormalizedContract


ROOT = Path(__file__).resolve().parents[2]
MARKET_PATH = ROOT / "data" / "market_transactions_mvp.csv"


def load_market_frame(path: Path = MARKET_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["exclusive_area_m2"] = pd.to_numeric(frame["exclusive_area_m2"], errors="coerce")
    frame["built_year"] = pd.to_numeric(frame["built_year"], errors="coerce")
    frame["price_or_deposit_won"] = pd.to_numeric(frame["price_or_deposit_won"], errors="coerce")
    return frame.dropna(subset=["exclusive_area_m2", "price_or_deposit_won"])


def iqr_filter(values: pd.Series) -> pd.Series:
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return values
    return values[(values >= q1 - 1.5 * iqr) & (values <= q3 + 1.5 * iqr)]


def similar_transactions(contract: NormalizedContract, trade_type: str, frame: pd.DataFrame | None = None) -> pd.DataFrame:
    data = frame if frame is not None else load_market_frame()
    same_type = data[
        (data["housing_type"] == contract.housing_type)
        & (data["trade_type"] == trade_type)
    ].copy()
    if same_type.empty:
        return same_type

    area = contract.exclusive_area_m2
    built_year = contract.built_year or same_type["built_year"].median()
    same_type["match_score"] = (
        np.where(same_type["legal_dong_code"].astype(str) == contract.legal_dong_code, 50, 0)
        + np.maximum(0, 30 - np.abs(same_type["exclusive_area_m2"] - area))
        + np.maximum(0, 20 - np.abs(same_type["built_year"] - built_year))
    )
    return same_type[same_type["match_score"] > 0].sort_values("match_score", ascending=False).head(20)


def market_summary(contract: NormalizedContract) -> dict[str, Any]:
    frame = load_market_frame()
    rent = similar_transactions(contract, "전세", frame)
    sale = similar_transactions(contract, "매매", frame)

    def stats(rows: pd.DataFrame) -> dict[str, Any]:
        if rows.empty:
            return {"count": 0, "median": 0, "min": 0, "max": 0}
        filtered = iqr_filter(rows["price_or_deposit_won"])
        return {
            "count": int(len(rows)),
            "median": int(filtered.median()) if len(filtered) else 0,
            "min": int(filtered.min()) if len(filtered) else 0,
            "max": int(filtered.max()) if len(filtered) else 0,
        }

    return {
      "rent": stats(rent),
      "sale": stats(sale),
      "similar_transaction_count": int(len(rent) + len(sale)),
    }
