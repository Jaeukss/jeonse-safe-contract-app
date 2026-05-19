from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "market_transactions_mvp.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
GWANAK_CODE_PREFIX = "11620"


HOUSING_MAP = {
    "아파트": "아파트",
    "오피스텔": "오피스텔",
    "연립": "연립다세대",
    "다세대": "연립다세대",
    "다가구": "다가구",
    "단독": "다가구",
}


def normalize_housing_type(value: object) -> str:
    text = str(value or "").strip()
    for key, mapped in HOUSING_MAP.items():
        if key in text:
            return mapped
    return text or "기타"


def split_dong(region: str) -> str:
    parts = str(region or "").split()
    return parts[-1] if parts else ""


def iqr_clip(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().empty:
        return numeric
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return numeric
    return numeric.clip(lower=q1 - 1.5 * iqr, upper=q3 + 1.5 * iqr)


def clean_trade_data(input_path: Path = DEFAULT_INPUT) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(input_path)
    price_column = "price_or_deposit_won" if "price_or_deposit_won" in df.columns else "price_won"
    df = df.rename(
        columns={
            "region": "region_text",
            "trade_type": "transaction_type",
            "trade_month": "transaction_ym",
            price_column: "amount_won",
            "exclusive_area_m2": "area_m2",
        }
    )
    df["law_dong_code"] = df["legal_dong_code"].astype(str)
    df = df[df["law_dong_code"].str.startswith(GWANAK_CODE_PREFIX) | df["region_text"].str.contains("관악구", na=False)]
    df = df.copy()
    df["district"] = "관악구"
    df["dong"] = df["region_text"].map(split_dong)
    df["housing_type"] = df["housing_type"].map(normalize_housing_type)
    df["transaction_type"] = df["transaction_type"].replace({"월세": "월세", "전세": "전세", "매매": "매매"})
    df["transaction_ym"] = pd.to_datetime(df["transaction_ym"], errors="coerce").dt.strftime("%Y-%m")
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["floor"] = pd.to_numeric(df["floor"], errors="coerce").fillna(0).astype(int)
    df["built_year"] = pd.to_numeric(df["built_year"], errors="coerce").fillna(0).astype(int)
    df["monthly_rent"] = pd.to_numeric(df.get("monthly_rent_won", 0), errors="coerce").fillna(0).astype(int)
    df["price"] = 0
    df["deposit"] = 0
    sale_mask = df["transaction_type"].eq("매매")
    df.loc[sale_mask, "price"] = pd.to_numeric(df.loc[sale_mask, "amount_won"], errors="coerce").fillna(0).astype(int)
    df.loc[~sale_mask, "deposit"] = pd.to_numeric(df.loc[~sale_mask, "amount_won"], errors="coerce").fillna(0).astype(int)
    df["amount_for_clip"] = df["price"].where(sale_mask, df["deposit"])
    df["amount_for_clip"] = df.groupby(["transaction_type", "housing_type"])["amount_for_clip"].transform(iqr_clip)
    df.loc[sale_mask, "price"] = df.loc[sale_mask, "amount_for_clip"].round().astype(int)
    df.loc[~sale_mask, "deposit"] = df.loc[~sale_mask, "amount_for_clip"].round().astype(int)

    columns = [
        "law_dong_code",
        "district",
        "dong",
        "housing_type",
        "transaction_type",
        "transaction_ym",
        "price",
        "deposit",
        "monthly_rent",
        "area_m2",
        "floor",
        "built_year",
    ]
    clean = df[columns].sort_values(["transaction_ym", "dong"], ascending=[False, True])
    rent = clean[clean["transaction_type"].isin(["전세", "월세"])].reset_index(drop=True)
    sale = clean[clean["transaction_type"].eq("매매")].reset_index(drop=True)
    return rent, sale


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rent, sale = clean_trade_data()
    rent.to_csv(PROCESSED_DIR / "ganak_rent_clean.csv", index=False, encoding="utf-8-sig")
    sale.to_csv(PROCESSED_DIR / "ganak_sale_clean.csv", index=False, encoding="utf-8-sig")
    print(f"wrote {len(rent)} rent rows and {len(sale)} sale rows")


if __name__ == "__main__":
    main()
