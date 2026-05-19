from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "building_registry_mvp.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
GWANAK_CODE_PREFIX = "11620"


def normalize_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "y", "yes", "위반", "위반건축물"}


def normalize_address(value: object) -> str:
    return " ".join(str(value or "").split())


def clean_building_data(input_path: Path = DEFAULT_INPUT, base_year: int = 2026) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    df["law_dong_code"] = df["legal_dong_code"].astype(str)
    df = df[df["law_dong_code"].str.startswith(GWANAK_CODE_PREFIX) | df["address"].str.contains("관악구", na=False)]
    df = df.copy()
    df["address_normalized"] = df["address"].map(normalize_address)
    df["road_address_normalized"] = df["road_address"].map(normalize_address)
    df["main_usage"] = df["main_use"].fillna("확인 불가")
    df["area_m2"] = pd.to_numeric(df["exclusive_area_m2"], errors="coerce")
    df["approval_year"] = pd.to_numeric(df["approval_year"], errors="coerce").fillna(0).astype(int)
    df["violation_flag"] = df["violation_flag"].map(normalize_bool)
    df["building_age"] = df["approval_year"].apply(lambda year: base_year - year if year else None)
    columns = [
        "law_dong_code",
        "address_normalized",
        "road_address_normalized",
        "building_name",
        "dong_name",
        "ho_name",
        "floor",
        "main_usage",
        "area_m2",
        "approval_year",
        "building_age",
        "violation_flag",
    ]
    return df[columns].reset_index(drop=True)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    clean = clean_building_data()
    clean.to_csv(PROCESSED_DIR / "ganak_building_clean.csv", index=False, encoding="utf-8-sig")
    print(f"wrote {len(clean)} building rows")


if __name__ == "__main__":
    main()
