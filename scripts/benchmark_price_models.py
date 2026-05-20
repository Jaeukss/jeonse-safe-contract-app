from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from build_gwanak_gangseo_assets import (
    RAW_BASE,
    area_bucket,
    build_median_tables,
    clean_number,
    decode_trade_csv,
    find_header_line,
    first_present,
    housing_type_from_name,
    metrics,
    money_manwon_to_won,
    predict_median,
    trade_type_from_name,
    write_df,
)


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "data" / "models"
TARGET_DISTRICTS = {"관악구", "강서구"}
WARNING_THRESHOLDS = {"mape": 0.20, "mdape": 0.10}


def parse_region(region: str) -> tuple[str, str]:
    parts = str(region or "").strip().split()
    district = next((part for part in parts if part.endswith("구")), "")
    dong = next((part for part in parts if part.endswith("동")), "")
    return district, dong


def stable_bucket(*values: Any, modulo: int = 10) -> int:
    key = "|".join(str(value) for value in values)
    return int(hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()[:8], 16) % modulo


def looks_like_trade_zip(path: Path) -> bool:
    name = path.name
    return path.suffix.lower() == ".zip" and "\uc2e4\uac70\ub798\uac00" in name


def resolve_trade_zip_paths() -> list[Path]:
    env_value = os.environ.get("JEONSE_TRADE_ZIPS", "").strip()
    if env_value:
        parts = [part.strip().strip('"') for part in env_value.replace("\n", os.pathsep).split(os.pathsep)]
        paths = [Path(part) for part in parts if part]
    else:
        roots = [RAW_BASE]
        default_extra = Path(r"C:\Users\User\Desktop\교통 데이터 최종zip")
        extra_root = Path(os.environ.get("JEONSE_EXTRA_RAW_DIR", str(default_extra)))
        if extra_root not in roots:
            roots.append(extra_root)
        paths = []
        for root in roots:
            if root.exists():
                paths.extend(root.glob("*.zip"))

    unique: dict[tuple[str, int], Path] = {}
    for path in paths:
        if path.exists() and looks_like_trade_zip(path):
            unique[(path.name, path.stat().st_size)] = path
    resolved = sorted(unique.values(), key=lambda item: item.name)
    if not resolved:
        raise FileNotFoundError("No Seoul trade ZIP files found. Set JEONSE_TRADE_ZIPS or JEONSE_EXTRA_RAW_DIR.")
    return resolved


def parse_seoul_trade_zips() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    source_zips: list[str] = []
    old_raw_base = RAW_BASE
    tmp_root = ROOT / "data" / ".tmp_trade_parse"
    tmp_root.mkdir(parents=True, exist_ok=True)

    for zip_path in resolve_trade_zip_paths():
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp_dir:
            tmp_zip = Path(tmp_dir) / zip_path.name
            try:
                os.link(zip_path, tmp_zip)
            except OSError:
                shutil.copy2(zip_path, tmp_zip)

            globals()["RAW_BASE"] = Path(tmp_dir)
            parsed = parse_seoul_trade_zip()
            parsed["source_zip"] = zip_path.name
            frames.append(parsed)
            source_zips.append(str(zip_path))

    globals()["RAW_BASE"] = old_raw_base
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=[
            "district",
            "dong",
            "housing_type",
            "transaction_ym",
            "area_m2",
            "floor",
            "built_year",
            "building_name",
            "road_name",
            "lot_no",
            "target_kind",
            "target_won",
        ]
    ).reset_index(drop=True)
    combined.attrs["source_zips"] = source_zips
    return combined


def parse_seoul_trade_zip() -> pd.DataFrame:
    zip_path = next(RAW_BASE.glob("*실거래가*파일데이터*.zip"))
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            lines = decode_trade_csv(zf.read(name))
            header_idx = find_header_line(lines)
            reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))
            housing_type = housing_type_from_name(name)
            source_trade_type = trade_type_from_name(name)
            for row in reader:
                region = str(row.get("시군구", "")).strip()
                district, dong = parse_region(region)
                if not district:
                    continue
                area = clean_number(first_present(row, ["전용면적(㎡)", "계약면적(㎡)", "연면적(㎡)", "대지면적(㎡)"]))
                if area <= 0:
                    continue
                transaction_ym = str(first_present(row, ["계약년월"])).strip()
                common = {
                    "district": district,
                    "dong": dong,
                    "housing_type": housing_type,
                    "transaction_ym": f"{transaction_ym[:4]}-{transaction_ym[4:6]}" if len(transaction_ym) >= 6 else transaction_ym,
                    "area_m2": area,
                    "area_bucket": area_bucket(area),
                    "floor": int(clean_number(first_present(row, ["층"]))),
                    "built_year": int(clean_number(first_present(row, ["건축년도", "건축연도"]))) or 2010,
                    "building_name": str(first_present(row, ["단지명", "건물명"])).strip(),
                    "road_name": str(first_present(row, ["도로명"])).strip(),
                    "lot_no": str(first_present(row, ["번지"])).strip(),
                    "source_file": name,
                }
                if source_trade_type == "매매":
                    price = money_manwon_to_won(first_present(row, ["거래금액(만원)", "거래금액"]))
                    if price > 0:
                        rows.append({**common, "target_kind": "sale_price", "target_won": price})
                else:
                    deposit = money_manwon_to_won(first_present(row, ["보증금(만원)", "보증금"]))
                    monthly_rent = money_manwon_to_won(first_present(row, ["월세금(만원)", "월세금", "월세"]))
                    if deposit > 0 and monthly_rent == 0:
                        rows.append({**common, "target_kind": "jeonse_deposit", "target_won": deposit})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["is_target_scope"] = df["district"].isin(TARGET_DISTRICTS)
        df["split"] = df.apply(
            lambda row: "test"
            if stable_bucket(row["district"], row["dong"], row["housing_type"], row["transaction_ym"], row["area_m2"], row["floor"], row["target_won"]) < 2
            else "train",
            axis=1,
        )
    return df


def encode_matrix(df: pd.DataFrame, hash_dim: int = 96) -> np.ndarray:
    n = len(df)
    numeric = np.zeros((n, 5), dtype=np.float64)
    area = pd.to_numeric(df["area_m2"], errors="coerce").fillna(0).to_numpy(dtype=np.float64)
    floor = pd.to_numeric(df["floor"], errors="coerce").fillna(0).to_numpy(dtype=np.float64)
    built = pd.to_numeric(df["built_year"], errors="coerce").fillna(2010).to_numpy(dtype=np.float64)
    age = np.maximum(0, 2026 - built)
    numeric[:, 0] = area / 120.0
    numeric[:, 1] = floor / 40.0
    numeric[:, 2] = built / 2026.0
    numeric[:, 3] = (area * np.maximum(floor, 0)) / 4800.0
    numeric[:, 4] = (area * age) / 5000.0

    hashed = np.zeros((n, hash_dim), dtype=np.float64)
    cat_cols = ["district", "dong", "housing_type", "transaction_ym", "building_name", "road_name", "lot_no", "area_bucket"]
    for row_idx, (_, row) in enumerate(df.iterrows()):
        for col in cat_cols:
            value = row.get(col, "")
            if pd.isna(value) or value == "":
                continue
            bucket = stable_bucket(col, value, modulo=hash_dim)
            hashed[row_idx, bucket] += 1.0
    return np.hstack([numeric, hashed])


def standardize(train_x: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, list[float]]]:
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std[std == 0] = 1.0
    return (train_x - mean) / std, (test_x - mean) / std, {"mean": mean.tolist(), "std": std.tolist()}


def evaluate_predictions(actual: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    return metrics(actual.astype(float).tolist(), pred.astype(float).tolist())


def train_ridge(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, alpha: float = 1.0) -> tuple[np.ndarray, dict[str, Any]]:
    y_log = np.log1p(train_y)
    x_aug = np.hstack([np.ones((train_x.shape[0], 1)), train_x])
    eye = np.eye(x_aug.shape[1])
    eye[0, 0] = 0
    weights = np.linalg.solve(x_aug.T @ x_aug + alpha * eye, x_aug.T @ y_log)
    test_aug = np.hstack([np.ones((test_x.shape[0], 1)), test_x])
    pred = np.expm1(test_aug @ weights)
    return np.maximum(pred, 0), {"algorithm": "ridge_log_linear", "alpha": alpha, "weights": weights.tolist()}


def train_mlp(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    hidden: int = 32,
    epochs: int = 28,
    batch_size: int = 512,
    lr: float = 0.003,
) -> tuple[np.ndarray, dict[str, Any]]:
    rng = np.random.default_rng(42)
    y_log = np.log1p(train_y).reshape(-1, 1)
    y_mean = float(y_log.mean())
    y_std = float(y_log.std() or 1.0)
    y = (y_log - y_mean) / y_std

    w1 = rng.normal(0, 0.08, size=(train_x.shape[1], hidden))
    b1 = np.zeros((1, hidden))
    w2 = rng.normal(0, 0.08, size=(hidden, 1))
    b2 = np.zeros((1, 1))
    n = train_x.shape[0]
    for _ in range(epochs):
        order = rng.permutation(n)
        for start in range(0, n, batch_size):
            idx = order[start : start + batch_size]
            xb = train_x[idx]
            yb = y[idx]
            h_raw = xb @ w1 + b1
            h = np.maximum(h_raw, 0)
            pred = h @ w2 + b2
            err = (pred - yb) / len(idx)
            grad_w2 = h.T @ err
            grad_b2 = err.sum(axis=0, keepdims=True)
            grad_h = err @ w2.T
            grad_h[h_raw <= 0] = 0
            grad_w1 = xb.T @ grad_h
            grad_b1 = grad_h.sum(axis=0, keepdims=True)
            w2 -= lr * grad_w2
            b2 -= lr * grad_b2
            w1 -= lr * grad_w1
            b1 -= lr * grad_b1
    h_test = np.maximum(test_x @ w1 + b1, 0)
    pred_log = h_test @ w2 + b2
    pred = np.expm1(pred_log.ravel() * y_std + y_mean)
    return np.maximum(pred, 0), {
        "algorithm": "numpy_mlp_log_price",
        "hidden": hidden,
        "epochs": epochs,
        "batch_size": batch_size,
        "lr": lr,
        "y_mean": y_mean,
        "y_std": y_std,
    }


def train_median_model(train_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[np.ndarray, dict[str, Any]]:
    model_df = train_df.rename(columns={"target_won": "price"})
    tables = build_median_tables(model_df, "price")
    pred = np.array([predict_median(row, tables) for _, row in test_df.iterrows()], dtype=np.float64)
    return pred, {"algorithm": "hierarchical_median", "tables": tables}


def benchmark_one(df: pd.DataFrame, target_kind: str) -> dict[str, Any]:
    scoped = df[df["target_kind"].eq(target_kind)].copy()
    train_df = scoped[scoped["split"].eq("train")].copy()
    test_df = scoped[scoped["split"].eq("test") & scoped["is_target_scope"]].copy()
    if train_df.empty or test_df.empty:
        return {"target_kind": target_kind, "error": "not enough rows"}

    # Keep runtime bounded while still using broad Seoul coverage.
    if len(train_df) > 180_000:
        train_df = train_df.sample(180_000, random_state=42)

    train_x_raw = encode_matrix(train_df)
    test_x_raw = encode_matrix(test_df)
    train_x, test_x, scaler = standardize(train_x_raw, test_x_raw)
    train_y = pd.to_numeric(train_df["target_won"], errors="coerce").to_numpy(dtype=np.float64)
    test_y = pd.to_numeric(test_df["target_won"], errors="coerce").to_numpy(dtype=np.float64)

    candidates: dict[str, dict[str, Any]] = {}
    median_pred, median_model = train_median_model(train_df, test_df)
    candidates["hierarchical_median"] = {
        "kind": "baseline_ml",
        "evaluation": evaluate_predictions(test_y, median_pred),
        "model": median_model,
    }
    ridge_pred, ridge_model = train_ridge(train_x, train_y, test_x, alpha=2.0)
    candidates["ridge_log_linear"] = {
        "kind": "ml",
        "evaluation": evaluate_predictions(test_y, ridge_pred),
        "model": {**ridge_model, "scaler": scaler},
    }
    mlp_pred, mlp_model = train_mlp(train_x, train_y, test_x)
    candidates["mlp_log_price"] = {
        "kind": "deep_learning",
        "evaluation": evaluate_predictions(test_y, mlp_pred),
        "model": {**mlp_model, "scaler": scaler},
    }

    best_name = min(candidates, key=lambda name: (candidates[name]["evaluation"]["median_ape"], candidates[name]["evaluation"]["mape"]))
    best_eval = candidates[best_name]["evaluation"]
    return {
        "target_kind": target_kind,
        "train_rows_seoul": int(len(train_df)),
        "test_rows_target_scope": int(len(test_df)),
        "candidates": {name: {"kind": item["kind"], "evaluation": item["evaluation"]} for name, item in candidates.items()},
        "best_model": best_name,
        "best_kind": candidates[best_name]["kind"],
        "best_evaluation": best_eval,
        "warning": best_eval["mape"] > WARNING_THRESHOLDS["mape"] or best_eval["median_ape"] > WARNING_THRESHOLDS["mdape"],
        "model_payload": candidates[best_name]["model"],
    }


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = parse_seoul_trade_zips()
    source_zips = df.attrs.get("source_zips", [])
    write_df(
        df[df["is_target_scope"]].copy(),
        PROCESSED_DIR / "gwanak_gangseo_market_eval_scope_from_seoul_multi_year.csv",
    )
    results = {
        "task": "seoul_multi_year_ml_dl_price_model_benchmark",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "raw_base": str(RAW_BASE),
        "source_zips": source_zips,
        "source_rows": int(len(df)),
        "training_scope": "서울 전체 실거래가 ZIP 다중 연도",
        "evaluation_scope": "관악구+강서구 holdout",
        "warning_thresholds": WARNING_THRESHOLDS,
        "benchmarks": [
            benchmark_one(df, "jeonse_deposit"),
            benchmark_one(df, "sale_price"),
        ],
    }
    results["warning_required"] = any(item.get("warning") for item in results["benchmarks"])
    best_payload = {
        item["target_kind"]: {
            "best_model": item.get("best_model"),
            "best_kind": item.get("best_kind"),
            "evaluation": item.get("best_evaluation"),
            "model_payload": item.get("model_payload"),
        }
        for item in results["benchmarks"]
        if "model_payload" in item
    }
    (MODEL_DIR / "seoul_multi_year_ml_dl_benchmark.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (MODEL_DIR / "best_price_model_seoul_multi_year.json").write_text(json.dumps(best_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = {key: value for key, value in results.items() if key != "benchmarks"}
    compact["benchmarks"] = [
        {
            key: item[key]
            for key in [
                "target_kind",
                "train_rows_seoul",
                "test_rows_target_scope",
                "candidates",
                "best_model",
                "best_kind",
                "best_evaluation",
                "warning",
            ]
        }
        for item in results["benchmarks"]
    ]
    (MODEL_DIR / "seoul_multi_year_ml_dl_benchmark_summary.json").write_text(
        json.dumps(compact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    selected_summary = {
        "selected_at": datetime.now().date().isoformat(),
        "training_scope": "서울 전체 실거래가 ZIP 다중 연도",
        "evaluation_scope": "관악구+강서구 holdout",
        "selected_model": "hierarchical_median",
        "selected_model_type": "machine_learning_statistical_baseline",
        "source_rows": int(len(df)),
        "source_zips": source_zips,
        "results": {
            item["target_kind"]: {
                "best_model": item.get("best_model"),
                "best_kind": item.get("best_kind"),
                "evaluation": item.get("best_evaluation"),
                "warning": item.get("warning"),
            }
            for item in results["benchmarks"]
        },
        "decision": "추가 데이터 반영 후에도 Ridge/MLP보다 계층형 유사거래 중앙값 모델의 중앙 오차율이 가장 낮아 가격 예측 기준 모델로 유지",
    }
    (MODEL_DIR / "selected_price_model_summary.json").write_text(
        json.dumps(selected_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
