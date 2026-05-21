from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW_BASE = Path(os.environ.get("JEONSE_RAW_DIR", r"C:\Users\User\Desktop\HWPX를_PDF로_1779283987915"))
PROCESSED_DIR = ROOT / "data" / "processed"
RAG_PROCESSED_DIR = ROOT / "data" / "rag_docs" / "processed"
MODEL_DIR = ROOT / "data" / "models"
ARTIFACT_DIR = ROOT / "artifacts"

TARGET_DISTRICTS = {
    "관악구": "11620",
    "강서구": "11500",
}

DISTRICT_DONG_CODES = {
    "관악구": {
        "봉천동": "1162010100",
        "신림동": "1162010200",
        "남현동": "1162010300",
    },
    "강서구": {
        "염창동": "1150010100",
        "등촌동": "1150010200",
        "화곡동": "1150010300",
        "가양동": "1150010400",
        "마곡동": "1150010500",
        "내발산동": "1150010600",
        "외발산동": "1150010700",
        "공항동": "1150010800",
        "방화동": "1150010900",
        "개화동": "1150011000",
        "과해동": "1150011100",
        "오곡동": "1150011200",
        "오쇠동": "1150011300",
    },
}

RAG_SOURCES = [
    ("법령", "주택임대차보호법_현행", "주택임대차보호법(법률)(제21065호)(20260102).doc"),
    ("법령", "주택임대차보호법_시행령", "주택임대차보호법 시행령(대통령령)(제35947호)(20260102).doc"),
    ("법령", "주택임대차보호법_제3조의6_하위법령", "주택임대차보호법_제3조의6_하위법령.pdf"),
    ("법령", "공인중개사법_시행규칙", "공인중개사법 시행규칙(국토교통부령)(제01349호)(20240710).doc"),
    ("계약서", "주택임대차_표준계약서", "주택임대차 표준계약서(원본게시용).pdf"),
    ("중개문서", "중개대상물_확인설명서", "[별지 제20호서식] 중개대상물 확인ㆍ설명서[Ⅰ] (주거용 건축물)[주택 유형(단독주택¸ 공동주택¸ 주거용 오피스텔)¸ 거래 형태(매매ㆍ교환¸ 임대)](공인중개사법 시행규칙).pdf"),
    ("HUG", "모바일보증_신청서류", "모바일보증 전세보증금반환보증 신청서류 일체.pdf"),
    ("HUG", "전세보증금반환보증_약관", "전세보증금반환보증약관(2024년도 4월 26일 개정).pdf"),
    ("예방안내", "국토교통부_전세계약_유의사항", "전세계약 유의사항 리플렛 (1).pdf"),
    ("예방안내", "서울시_전세사기_예방_A_to_Z", "전세 계약. 두렵지 않아요 전세 사기 예방 A to Z.pdf"),
    ("신고안내", "임대차계약신고_매뉴얼", "lsstManualDownload.pdf"),
]


def clean_number(value: Any) -> float:
    text = str(value or "").replace(",", "").replace('"', "").strip()
    if not text or text in {"-", "nan", "None"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def money_manwon_to_won(value: Any) -> int:
    return int(round(clean_number(value) * 10_000))


def first_present(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row and str(row.get(name, "")).strip() not in {"", "-"}:
            return row.get(name)
    return ""


def parse_district(region: str) -> tuple[str, str, str]:
    for district, sigungu_code in TARGET_DISTRICTS.items():
        if district in region:
            match = re.search(rf"{district}\s+([가-힣0-9]+동)", region)
            dong = match.group(1) if match else ""
            law_code = DISTRICT_DONG_CODES.get(district, {}).get(dong, sigungu_code)
            return district, dong, law_code
    return "", "", ""


def housing_type_from_name(name: str) -> str:
    if "아파트" in name:
        return "아파트"
    if "오피스텔" in name:
        return "오피스텔"
    if "연립다세대" in name:
        return "연립다세대"
    if "단독다가구" in name:
        return "다가구"
    return "기타"


def trade_type_from_name(name: str) -> str:
    if "(매매)" in name:
        return "매매"
    return "전월세"


def decode_trade_csv(raw: bytes) -> list[str]:
    for enc in ("cp949", "euc-kr", "utf-8-sig"):
        try:
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return raw.decode("cp949", errors="replace").splitlines()


def find_header_line(lines: list[str]) -> int:
    for idx, line in enumerate(lines):
        if "시군구" in line and ("거래금액" in line or "보증금" in line):
            return idx
    raise ValueError("실거래가 CSV 헤더를 찾지 못했습니다.")


def process_trade_zip() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    zip_path = next(RAW_BASE.glob("*실거래가*파일데이터*.zip"))
    rent_rows: list[dict[str, Any]] = []
    sale_rows: list[dict[str, Any]] = []
    file_count = 0
    source_rows = 0

    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            file_count += 1
            raw = zf.read(name)
            lines = decode_trade_csv(raw)
            header_idx = find_header_line(lines)
            reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))
            housing_type = housing_type_from_name(name)
            source_trade_type = trade_type_from_name(name)

            for row in reader:
                source_rows += 1
                region = str(row.get("시군구", "")).strip()
                district, dong, legal_dong_code = parse_district(region)
                if not district:
                    continue
                area = clean_number(first_present(row, ["전용면적(㎡)", "계약면적(㎡)", "연면적(㎡)", "대지면적(㎡)"]))
                if area <= 0:
                    continue
                floor = int(clean_number(first_present(row, ["층"])))
                built_year = int(clean_number(first_present(row, ["건축년도", "건축연도"]))) or None
                transaction_ym = str(first_present(row, ["계약년월"])).strip()
                road_name = str(first_present(row, ["도로명"])).strip()
                lot_no = str(first_present(row, ["번지"])).strip()
                building_name = str(first_present(row, ["단지명", "건물명"])).strip()

                base = {
                    "law_dong_code": legal_dong_code,
                    "sigungu_code": TARGET_DISTRICTS[district],
                    "district": district,
                    "dong": dong,
                    "address": region,
                    "lot_no": lot_no,
                    "road_name": road_name,
                    "building_name": building_name,
                    "housing_type": housing_type,
                    "transaction_ym": f"{transaction_ym[:4]}-{transaction_ym[4:6]}" if len(transaction_ym) >= 6 else transaction_ym,
                    "area_m2": area,
                    "floor": floor,
                    "built_year": built_year,
                    "source_file": name,
                }
                if source_trade_type == "매매":
                    price = money_manwon_to_won(first_present(row, ["거래금액(만원)", "거래금액"]))
                    if price <= 0:
                        continue
                    sale_rows.append({**base, "transaction_type": "매매", "price": price})
                else:
                    deposit = money_manwon_to_won(first_present(row, ["보증금(만원)", "보증금"]))
                    monthly_rent = money_manwon_to_won(first_present(row, ["월세금(만원)", "월세금", "월세"]))
                    if deposit <= 0:
                        continue
                    rent_rows.append(
                        {
                            **base,
                            "transaction_type": "월세" if monthly_rent > 0 else "전세",
                            "deposit": deposit,
                            "monthly_rent": monthly_rent,
                        }
                    )

    rent_df = pd.DataFrame(rent_rows)
    sale_df = pd.DataFrame(sale_rows)
    return rent_df, sale_df, {
        "source_zip": str(zip_path),
        "source_files": file_count,
        "source_rows_scanned": source_rows,
        "rent_rows": int(len(rent_df)),
        "sale_rows": int(len(sale_df)),
    }


def write_df(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_target_building_zip(zip_pattern: str, columns: dict[str, str]) -> pd.DataFrame:
    zip_path = next(RAW_BASE.glob(zip_pattern))
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            if not any(district in name for district in TARGET_DISTRICTS):
                continue
            with zf.open(name) as handle:
                for chunk in pd.read_csv(handle, encoding="utf-8-sig", dtype=str, chunksize=100_000):
                    if "시군구코드" in chunk.columns:
                        chunk = chunk[chunk["시군구코드"].isin(TARGET_DISTRICTS.values())]
                    if chunk.empty:
                        continue
                    selected = pd.DataFrame()
                    for source, target in columns.items():
                        selected[target] = chunk[source] if source in chunk.columns else ""
                    selected["source_file"] = name
                    frames.append(selected)
    if not frames:
        return pd.DataFrame(columns=list(columns.values()) + ["source_file"])
    return pd.concat(frames, ignore_index=True)


def process_building_data() -> dict[str, Any]:
    title_cols = {
        "대지위치": "lot_address",
        "도로명대지위치": "road_address",
        "시군구코드": "sigungu_code",
        "법정동코드": "legal_dong_code",
        "대지구분코드": "land_type_code",
        "번": "bun",
        "지": "ji",
        "관리건축물대장PK": "building_register_pk",
        "대장구분코드명": "register_type_name",
        "대장종류코드명": "register_kind_name",
        "건물명": "building_name",
        "주용도코드명": "main_usage",
        "기타용도": "other_usage",
        "연면적(㎡)": "gross_area_m2",
        "건축면적(㎡)": "building_area_m2",
        "사용승인일": "approval_date",
        "위반건축물여부": "violation_flag",
        "생성일자": "source_created_date",
    }
    exclusive_cols = {
        "대지위치": "lot_address",
        "도로명대지위치": "road_address",
        "시군구코드": "sigungu_code",
        "법정동코드": "legal_dong_code",
        "대지구분코드": "land_type_code",
        "번": "bun",
        "지": "ji",
        "관리건축물대장PK": "building_register_pk",
        "대장구분코드명": "register_type_name",
        "대장종류코드명": "register_kind_name",
        "건물명": "building_name",
        "동명칭": "dong_name",
        "호명칭": "ho_name",
        "층번호": "floor",
        "생성일자": "source_created_date",
    }
    exclusive_area_cols = {
        "대지위치": "lot_address",
        "도로명대지위치": "road_address",
        "시군구코드": "sigungu_code",
        "법정동코드": "legal_dong_code",
        "관리건축물대장PK": "building_register_pk",
        "건물명": "building_name",
        "동명칭": "dong_name",
        "호명칭": "ho_name",
        "층번호": "floor",
        "전유공용구분코드명": "area_type_name",
        "주용도코드명": "main_usage",
        "면적(㎡)": "area_m2",
        "생성일자": "source_created_date",
    }
    floor_cols = {
        "대지위치": "lot_address",
        "도로명대지위치": "road_address",
        "시군구코드": "sigungu_code",
        "법정동코드": "legal_dong_code",
        "관리건축물대장PK": "building_register_pk",
        "건물명": "building_name",
        "층번호": "floor",
        "층번호명": "floor_name",
        "주용도코드명": "main_usage",
        "면적(㎡)": "area_m2",
        "생성일자": "source_created_date",
    }
    recap_cols = {
        "대지위치": "lot_address",
        "도로명대지위치": "road_address",
        "시군구코드": "sigungu_code",
        "법정동코드": "legal_dong_code",
        "관리건축물대장PK": "building_register_pk",
        "건물명": "building_name",
        "대지면적(㎡)": "land_area_m2",
        "건축면적(㎡)": "building_area_m2",
        "연면적(㎡)": "gross_area_m2",
        "주용도코드명": "main_usage",
        "세대수(세대)": "household_count",
        "호수(호)": "unit_count",
        "생성일자": "source_created_date",
    }

    outputs = {
        "building_title": read_target_building_zip("*(서울)*_표제부*.zip", title_cols),
        "building_exclusive": read_target_building_zip("*(서울)*전유부*.zip", exclusive_cols),
        "building_exclusive_area": read_target_building_zip("*(서울)*전유공용면적*.zip", exclusive_area_cols),
        "building_floor": read_target_building_zip("*(서울)*층별개요*.zip", floor_cols),
        "building_recap_title": read_target_building_zip("*(서울)*총괄표제부*.zip", recap_cols),
    }

    # Normalize common numeric/date fields.
    for df in outputs.values():
        if "sigungu_code" in df:
            df["district"] = df["sigungu_code"].map({v: k for k, v in TARGET_DISTRICTS.items()}).fillna("")
        for col in ["area_m2", "gross_area_m2", "building_area_m2", "land_area_m2"]:
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "floor" in df:
            df["floor"] = pd.to_numeric(df["floor"], errors="coerce")
        if "approval_date" in df:
            df["approval_year"] = pd.to_numeric(df["approval_date"].astype(str).str[:4], errors="coerce")
        if "violation_flag" in df:
            df["violation_flag"] = df["violation_flag"].astype(str).str.contains("위반|Y|1|true", case=False, na=False)

    paths = {
        "building_title": PROCESSED_DIR / "gwanak_gangseo_building_title_clean.csv",
        "building_exclusive": PROCESSED_DIR / "gwanak_gangseo_building_exclusive_clean.csv",
        "building_exclusive_area": PROCESSED_DIR / "gwanak_gangseo_building_exclusive_area_clean.csv",
        "building_floor": PROCESSED_DIR / "gwanak_gangseo_building_floor_clean.csv",
        "building_recap_title": PROCESSED_DIR / "gwanak_gangseo_building_recap_title_clean.csv",
    }
    for key, df in outputs.items():
        write_df(df, paths[key])

    title = outputs["building_title"].copy()
    if not title.empty:
        app_building = pd.DataFrame(
            {
                "address_normalized": title["lot_address"].fillna("").astype(str),
                "road_address": title["road_address"].fillna("").astype(str),
                "district": title["district"],
                "main_usage": title["main_usage"].fillna(""),
                "area_m2": title.get("gross_area_m2", pd.Series(dtype=float)),
                "approval_year": title.get("approval_year", pd.Series(dtype=float)),
                "violation_flag": title.get("violation_flag", pd.Series(dtype=bool)),
                "building_register_pk": title["building_register_pk"],
            }
        )
        write_df(app_building, PROCESSED_DIR / "ganak_building_clean.csv")

    return {key: {"rows": int(len(df)), "file": str(paths[key])} for key, df in outputs.items()}


def process_house_price_data() -> dict[str, Any]:
    cols = {
        "대지위치": "lot_address",
        "도로명대지위치": "road_address",
        "시군구코드": "sigungu_code",
        "법정동코드": "legal_dong_code",
        "대지구분코드": "land_type_code",
        "번": "bun",
        "지": "ji",
        "관리건축물대장PK": "building_register_pk",
        "대장구분코드명": "register_type_name",
        "대장종류코드명": "register_kind_name",
        "건물명": "building_name",
        "기준일자": "price_base_date",
        "주택가격": "official_house_price",
        "생성일자": "source_created_date",
    }
    frames: list[pd.DataFrame] = []
    scanned = 0
    for zip_path in sorted(RAW_BASE.glob("*(서울)*주택가격*.zip")):
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                with zf.open(name) as handle:
                    for chunk in pd.read_csv(handle, encoding="utf-8-sig", dtype=str, chunksize=150_000):
                        scanned += len(chunk)
                        if "시군구코드" in chunk.columns:
                            chunk = chunk[chunk["시군구코드"].isin(TARGET_DISTRICTS.values())]
                        if chunk.empty:
                            continue
                        selected = pd.DataFrame()
                        for source, target in cols.items():
                            selected[target] = chunk[source] if source in chunk.columns else ""
                        selected["source_file"] = name
                        frames.append(selected)
    house_price = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=list(cols.values()) + ["source_file"])
    house_price["district"] = house_price["sigungu_code"].map({v: k for k, v in TARGET_DISTRICTS.items()}).fillna("")
    house_price["price_base_date"] = pd.to_numeric(house_price["price_base_date"], errors="coerce")
    house_price["official_house_price"] = pd.to_numeric(house_price["official_house_price"], errors="coerce")
    house_price = house_price.dropna(subset=["building_register_pk", "price_base_date", "official_house_price"])
    latest = (
        house_price.sort_values(["building_register_pk", "price_base_date"])
        .groupby("building_register_pk", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    latest_path = PROCESSED_DIR / "gwanak_gangseo_official_house_price_latest.csv"
    write_df(latest, latest_path)
    return {
        "source_rows_scanned": int(scanned),
        "history_rows": int(len(house_price)),
        "latest_rows": int(len(latest)),
        "latest_file": str(latest_path),
        "latest_base_date_max": int(latest["price_base_date"].max()) if not latest.empty else None,
    }


def stable_split(row: pd.Series) -> str:
    key = "|".join(
        str(row.get(col, ""))
        for col in ["district", "dong", "housing_type", "transaction_ym", "area_m2", "floor", "price"]
    )
    bucket = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % 10
    return "test" if bucket < 2 else "train"


def area_bucket(value: Any) -> int:
    area = clean_number(value)
    return int(area // 5 * 5) if area else 0


def build_median_tables(train: pd.DataFrame, target_col: str) -> dict[str, dict[str, float]]:
    train = train.copy()
    train["area_bucket"] = train["area_m2"].apply(area_bucket)
    specs = {
        "district_dong_type_building_area": ["district", "dong", "housing_type", "building_name", "area_bucket"],
        "district_dong_type_road_area": ["district", "dong", "housing_type", "road_name", "area_bucket"],
        "district_dong_type_lot_area": ["district", "dong", "housing_type", "lot_no", "area_bucket"],
        "district_dong_type_building": ["district", "dong", "housing_type", "building_name"],
        "district_dong_type_road": ["district", "dong", "housing_type", "road_name"],
        "district_dong_type_lot": ["district", "dong", "housing_type", "lot_no"],
        "district_dong_type_area": ["district", "dong", "housing_type", "area_bucket"],
        "district_type_area": ["district", "housing_type", "area_bucket"],
        "district_type": ["district", "housing_type"],
        "type_area": ["housing_type", "area_bucket"],
        "type": ["housing_type"],
        "global": [],
    }
    tables: dict[str, dict[str, float]] = {}
    for name, cols in specs.items():
        if not cols:
            tables[name] = {"*": float(train[target_col].median())}
            continue
        grouped = train.groupby(cols)[target_col].median()
        tables[name] = {"|".join(map(str, idx if isinstance(idx, tuple) else (idx,))): float(value) for idx, value in grouped.items()}
    return tables


def predict_median(row: pd.Series, tables: dict[str, dict[str, float]]) -> float:
    bucket = area_bucket(row.get("area_m2"))
    candidates = [
        ("district_dong_type_building_area", [row.get("district"), row.get("dong"), row.get("housing_type"), row.get("building_name"), bucket]),
        ("district_dong_type_road_area", [row.get("district"), row.get("dong"), row.get("housing_type"), row.get("road_name"), bucket]),
        ("district_dong_type_lot_area", [row.get("district"), row.get("dong"), row.get("housing_type"), row.get("lot_no"), bucket]),
        ("district_dong_type_building", [row.get("district"), row.get("dong"), row.get("housing_type"), row.get("building_name")]),
        ("district_dong_type_road", [row.get("district"), row.get("dong"), row.get("housing_type"), row.get("road_name")]),
        ("district_dong_type_lot", [row.get("district"), row.get("dong"), row.get("housing_type"), row.get("lot_no")]),
        ("district_dong_type_area", [row.get("district"), row.get("dong"), row.get("housing_type"), bucket]),
        ("district_type_area", [row.get("district"), row.get("housing_type"), bucket]),
        ("district_type", [row.get("district"), row.get("housing_type")]),
        ("type_area", [row.get("housing_type"), bucket]),
        ("type", [row.get("housing_type")]),
    ]
    for table_name, values in candidates:
        key = "|".join(map(str, values))
        if key in tables.get(table_name, {}):
            return tables[table_name][key]
    return tables["global"]["*"]


def metrics(actual: list[float], pred: list[float]) -> dict[str, float]:
    if not actual:
        return {"rows": 0, "mae_won": 0, "rmse_won": 0, "mape": 0, "median_ape": 0}
    errors = [p - a for p, a in zip(pred, actual)]
    abs_errors = [abs(e) for e in errors]
    ape = [abs(p - a) / max(a, 1.0) for p, a in zip(pred, actual)]
    return {
        "rows": len(actual),
        "mae_won": int(round(sum(abs_errors) / len(abs_errors))),
        "rmse_won": int(round(math.sqrt(sum(e * e for e in errors) / len(errors)))),
        "mape": round(sum(ape) / len(ape), 4),
        "median_ape": round(statistics.median(ape), 4),
    }


def train_and_evaluate_models(rent: pd.DataFrame, sale: pd.DataFrame) -> dict[str, Any]:
    results: dict[str, Any] = {
        "task": "gwanak_gangseo_price_reference_model",
        "threshold": {"mape_warning": 0.20},
        "method": "hierarchical median estimator by district, dong, housing type, and area bucket",
        "models": {},
        "warning_required": False,
    }
    model_tables: dict[str, Any] = {}

    datasets = {
        "jeonse_deposit": (rent[rent["transaction_type"].eq("전세")].copy(), "deposit"),
        "sale_price": (sale.copy(), "price"),
    }
    for model_name, (df, target_col) in datasets.items():
        df = df.dropna(subset=[target_col, "area_m2"]).copy()
        df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
        df = df[df[target_col] > 0]
        df["split"] = df.apply(stable_split, axis=1)
        train = df[df["split"].eq("train")].copy()
        test = df[df["split"].eq("test")].copy()
        if train.empty or test.empty:
            results["models"][model_name] = {"train_rows": len(train), "test_rows": len(test), "evaluation": metrics([], [])}
            continue
        tables = build_median_tables(train, target_col)
        predictions = [predict_median(row, tables) for _, row in test.iterrows()]
        actuals = [float(value) for value in test[target_col].tolist()]
        evaluation = metrics(actuals, predictions)
        warning = evaluation["mape"] > results["threshold"]["mape_warning"]
        results["models"][model_name] = {
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "target_col": target_col,
            "evaluation": evaluation,
            "warning": bool(warning),
        }
        if warning:
            results["warning_required"] = True
        model_tables[model_name] = tables

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (MODEL_DIR / "gwanak_gangseo_price_model_eval.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (MODEL_DIR / "gwanak_gangseo_price_model_tables.json").write_text(json.dumps(model_tables, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def rtf_to_text(data: bytes) -> str:
    text = data.decode("latin1", errors="ignore")

    def unicode_repl(match: re.Match[str]) -> str:
        code = int(match.group(1))
        if code < 0:
            code += 65536
        return chr(code)

    text = re.sub(r"\\u(-?\d+).", unicode_repl, text)
    text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("cp949", errors="ignore"), text)
    text = re.sub(r"\\(par|line|tab)\b ?", lambda m: "\n" if m.group(1) in {"par", "line"} else "\t", text)
    text = re.sub(r"\\[a-zA-Z]+\d* ?", "", text)
    text = re.sub(r"[{}]", "", text)
    text = text.replace("\\~", " ").replace("\\-", "-").replace("\\_", "-")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


BAD_TEXT_MARKERS = (
    "\x00",
    "8BIM",
    "Adobe Photoshop",
    "Times New Roman",
    "xpacket",
    "JFIF",
    "Exif",
    "ÿØ",
    "ÿÙ",
)


def _looks_like_binary_line(line: str) -> bool:
    if any(marker in line for marker in BAD_TEXT_MARKERS):
        return True
    if not line:
        return True
    visible = sum(1 for char in line if char.isprintable() or char.isspace())
    korean = sum(1 for char in line if "가" <= char <= "힣")
    ascii_word = sum(1 for char in line if char.isalnum())
    return (visible / max(len(line), 1) < 0.75) or (korean == 0 and ascii_word < 12 and len(line) > 80)


def clean_extracted_text(text: str) -> str:
    text = text.replace("\x00", "")
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if _looks_like_binary_line(line):
            continue
        line = re.sub(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ\s.,;:()\[\]{}<>/\-+*=_%·ㆍ「」『』“”\"'?!㎡]", " ", line)
        line = re.sub(r"\s+", " ", line).strip()
        korean = sum(1 for char in line if "가" <= char <= "힣")
        if len(line) > 80 and korean < 3 and not any(token in line for token in ("http", "HUG", "PDF", "Mobile")):
            continue
        if len(line) < 4:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def extract_document_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return clean_extracted_text(extract_pdf_text(path))
    if path.suffix.lower() == ".doc":
        return clean_extracted_text(rtf_to_text(path.read_bytes()))
    return clean_extracted_text(path.read_text(encoding="utf-8", errors="ignore"))


def slugify(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def chunk_text(text: str, size: int = 1200, overlap: int = 160) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk = clean_extracted_text(text[start:end].strip())
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def build_rag_docs() -> dict[str, Any]:
    RAG_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    corpus_path = RAG_PROCESSED_DIR / "rag_corpus_gwanak_gangseo.jsonl"
    source_manifest: list[dict[str, Any]] = []
    chunk_count = 0
    with corpus_path.open("w", encoding="utf-8") as corpus_file:
        for category, title, file_name in RAG_SOURCES:
            path = RAW_BASE / file_name
            slug = slugify(title)
            md_path = RAG_PROCESSED_DIR / f"{slug}.md"
            if not path.exists():
                if md_path.exists():
                    existing = md_path.read_text(encoding="utf-8", errors="ignore")
                    text = clean_extracted_text(existing)
                    source_status = "processed_from_existing_md"
                else:
                    source_manifest.append({"category": category, "title": title, "source_file": str(path), "status": "missing"})
                    continue
            else:
                text = extract_document_text(path)
                source_status = "processed"
            md_path.write_text(
                f"# {title}\n\n- category: {category}\n- source_file: {path.name}\n- processed_at: {datetime.now().isoformat(timespec='seconds')}\n\n{text}\n",
                encoding="utf-8",
            )
            chunks = chunk_text(text)
            for idx, chunk in enumerate(chunks, start=1):
                corpus_file.write(
                    json.dumps(
                        {
                            "id": f"{slug}-{idx:04d}",
                            "title": title,
                            "category": category,
                            "source_file": path.name,
                            "chunk_index": idx,
                            "text": chunk,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            chunk_count += len(chunks)
            source_manifest.append(
                {
                    "category": category,
                    "title": title,
                    "source_file": str(path),
                    "processed_file": str(md_path),
                    "characters": len(text),
                    "chunks": len(chunks),
                    "status": source_status,
                }
            )
    manifest_path = RAG_PROCESSED_DIR / "rag_source_manifest_gwanak_gangseo.json"
    manifest_path.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "source_count": len(source_manifest),
        "processed_sources": sum(1 for item in source_manifest if item["status"].startswith("processed")),
        "chunk_count": chunk_count,
        "corpus_file": str(corpus_path),
        "manifest_file": str(manifest_path),
    }


def write_market_outputs(rent: pd.DataFrame, sale: pd.DataFrame) -> dict[str, Any]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rent = rent.sort_values(["district", "dong", "housing_type", "transaction_ym"]).reset_index(drop=True)
    sale = sale.sort_values(["district", "dong", "housing_type", "transaction_ym"]).reset_index(drop=True)
    combined = pd.concat(
        [
            rent.assign(price_or_deposit_won=rent["deposit"]),
            sale.assign(price_or_deposit_won=sale["price"], monthly_rent=0),
        ],
        ignore_index=True,
        sort=False,
    )
    paths = {
        "rent": PROCESSED_DIR / "gwanak_gangseo_rent_clean.csv",
        "sale": PROCESSED_DIR / "gwanak_gangseo_sale_clean.csv",
        "combined": PROCESSED_DIR / "gwanak_gangseo_market_transactions_clean.csv",
    }
    write_df(rent, paths["rent"])
    write_df(sale, paths["sale"])
    write_df(combined, paths["combined"])

    # Compatibility paths used by the Streamlit MVP before this expansion.
    write_df(rent, PROCESSED_DIR / "ganak_rent_clean.csv")
    write_df(sale, PROCESSED_DIR / "ganak_sale_clean.csv")
    return {
        "rent_rows": int(len(rent)),
        "sale_rows": int(len(sale)),
        "combined_rows": int(len(combined)),
        "files": {key: str(path) for key, path in paths.items()},
    }


def create_final_zip(manifest: dict[str, Any]) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ARTIFACT_DIR / "gwanak_gangseo_processing_report.json"
    report_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = ARTIFACT_DIR / "gwanak_gangseo_final_used_files.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        include_files = []
        include_files.extend(PROCESSED_DIR.glob("gwanak_gangseo_*.csv"))
        include_files.extend(
            [
                PROCESSED_DIR / "ganak_rent_clean.csv",
                PROCESSED_DIR / "ganak_sale_clean.csv",
                PROCESSED_DIR / "ganak_building_clean.csv",
            ]
        )
        include_files.extend(RAG_PROCESSED_DIR.glob("*"))
        include_files.extend(MODEL_DIR.glob("gwanak_gangseo_*"))
        for path in include_files:
            if path.is_file():
                zf.write(path, path.relative_to(ROOT))
        zf.write(report_path, report_path.relative_to(ROOT))
    return zip_path


def main() -> None:
    if not RAW_BASE.exists():
        raise SystemExit(f"원천 자료 폴더를 찾을 수 없습니다: {RAW_BASE}")

    rent, sale, trade_summary = process_trade_zip()
    market_summary = write_market_outputs(rent, sale)
    building_summary = process_building_data()
    house_price_summary = process_house_price_data()
    rag_summary = build_rag_docs()
    model_eval = train_and_evaluate_models(rent, sale)

    manifest = {
        "project": "관악구+강서구 전세계약 위험진단 MVP",
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "raw_base": str(RAW_BASE),
        "scope": {"districts": TARGET_DISTRICTS},
        "trade_summary": trade_summary,
        "market_outputs": market_summary,
        "building_outputs": building_summary,
        "house_price_outputs": house_price_summary,
        "rag_outputs": rag_summary,
        "model_evaluation": model_eval,
        "notes": [
            "최종 ZIP에는 원본 ZIP/PDF/DOC를 넣지 않고 전처리 산출물만 포함했습니다.",
            "주택가격은 최신 기준일자 기준 건축물대장PK별 1행만 보조 피처로 사용합니다.",
            "모델 성능 경고선은 MVP 회귀 기준 MAPE 20%로 설정했습니다.",
        ],
    }
    zip_path = create_final_zip(manifest)
    print(json.dumps({"final_zip": str(zip_path), **manifest}, ensure_ascii=False, indent=2))
    if model_eval.get("warning_required"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
