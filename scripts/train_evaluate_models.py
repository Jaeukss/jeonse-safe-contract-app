from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKET_PATH = ROOT / "data" / "market_transactions_mvp.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "models"

HOUSING_TYPE_MAP = {
    "아파트": "아파트",
    "APT": "아파트",
    "apartment": "아파트",
    "오피스텔": "오피스텔",
    "officetel": "오피스텔",
    "연립다세대": "연립다세대",
    "연립": "연립다세대",
    "다세대": "연립다세대",
    "다가구": "다가구",
    "단독": "단독주택",
    "단독주택": "단독주택",
}

FEATURE_NAMES = [
    "exclusive_area_m2",
    "floor",
    "built_year",
    "area_x_floor",
    "area_x_age",
    "dong_hash_00",
    "dong_hash_01",
    "dong_hash_02",
    "dong_hash_03",
    "type_apt",
    "type_officetel",
    "type_villa",
    "type_multi_family",
    "type_detached",
]


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def to_float(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def to_int(value: Any) -> int:
    return int(round(to_float(value)))


def normalize_housing_type(value: str) -> str:
    key = str(value or "").strip()
    return HOUSING_TYPE_MAP.get(key, HOUSING_TYPE_MAP.get(key.lower(), key))


def preprocess_market(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    processed = []
    for row in rows:
        price = to_int(row.get("price_or_deposit_won") or row.get("price_won"))
        area = to_float(row.get("exclusive_area_m2"))
        if price <= 0 or area <= 0:
            continue
        trade_month = str(row.get("trade_month", "")).strip().replace("-", "")
        processed.append(
            {
                "region": str(row.get("region", "")).strip(),
                "legal_dong_code": str(row.get("legal_dong_code", "")).strip(),
                "housing_type": normalize_housing_type(str(row.get("housing_type", ""))),
                "trade_type": str(row.get("trade_type", "")).strip(),
                "trade_month": trade_month,
                "price_or_deposit_won": price,
                "monthly_rent_won": to_int(row.get("monthly_rent_won")),
                "exclusive_area_m2": round(area, 3),
                "floor": to_int(row.get("floor")),
                "built_year": to_int(row.get("built_year")) or 2010,
                "normalized_basis": "원 단위, 제곱미터 단위, 표준 주택유형, 최근 거래 중심",
            }
        )
    return iqr_clip(processed)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    return ordered[lower] * (upper - pos) + ordered[upper] * (pos - lower)


def iqr_clip(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[int]] = {}
    for row in rows:
        key = (row["legal_dong_code"], row["housing_type"], row["trade_type"])
        groups.setdefault(key, []).append(int(row["price_or_deposit_won"]))
    limits = {}
    for key, values in groups.items():
        if len(values) < 4:
            limits[key] = (min(values), max(values))
            continue
        q1 = percentile([float(v) for v in values], 0.25)
        q3 = percentile([float(v) for v in values], 0.75)
        iqr = max(q3 - q1, 1)
        limits[key] = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    clipped = []
    for row in rows:
        key = (row["legal_dong_code"], row["housing_type"], row["trade_type"])
        low, high = limits[key]
        original = row["price_or_deposit_won"]
        row = dict(row)
        row["price_or_deposit_won"] = int(min(max(original, low), high))
        row["outlier_clip_applied"] = int(row["price_or_deposit_won"] != original)
        clipped.append(row)
    return clipped


def stable_bucket(value: str, buckets: int = 4) -> int:
    digest = hashlib.sha1(str(value).encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) % buckets


def feature_vector(row: dict[str, Any]) -> list[float]:
    area = float(row["exclusive_area_m2"])
    floor = float(row["floor"])
    built_year = float(row["built_year"])
    age = max(0.0, 2026.0 - built_year)
    dong_bucket = stable_bucket(row["legal_dong_code"], 4)
    housing_type = row["housing_type"]
    values = [
        area / 120.0,
        floor / 40.0,
        built_year / 2026.0,
        (area * floor) / 4800.0,
        (area * age) / 4000.0,
    ]
    values.extend(1.0 if dong_bucket == i else 0.0 for i in range(4))
    values.extend(
        [
            1.0 if housing_type == "아파트" else 0.0,
            1.0 if housing_type == "오피스텔" else 0.0,
            1.0 if housing_type == "연립다세대" else 0.0,
            1.0 if housing_type == "다가구" else 0.0,
            1.0 if housing_type == "단독주택" else 0.0,
        ]
    )
    return values


def train_test_split(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = []
    test = []
    for row in rows:
        key = "|".join(str(row.get(part, "")) for part in ["legal_dong_code", "trade_month", "price_or_deposit_won", "exclusive_area_m2", "floor"])
        bucket = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % 10
        (test if bucket < 2 else train).append(row)
    if not test and rows:
        split = max(1, len(rows) // 5)
        test = rows[:split]
        train = rows[split:]
    return train, test


def fit_standardizer(vectors: list[list[float]]) -> tuple[list[float], list[float]]:
    width = len(vectors[0])
    means = [sum(vec[i] for vec in vectors) / len(vectors) for i in range(width)]
    stds = []
    for i in range(width):
        variance = sum((vec[i] - means[i]) ** 2 for vec in vectors) / len(vectors)
        stds.append(math.sqrt(variance) or 1.0)
    return means, stds


def transform(vec: list[float], means: list[float], stds: list[float]) -> list[float]:
    return [(vec[i] - means[i]) / (stds[i] or 1.0) for i in range(len(vec))]


def train_regressor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"weights": [], "bias": 0.0, "means": [], "stds": [], "target_median": 0}
    raw_vectors = [feature_vector(row) for row in rows]
    targets = [math.log1p(float(row["price_or_deposit_won"])) for row in rows]
    means, stds = fit_standardizer(raw_vectors)
    vectors = [transform(vec, means, stds) for vec in raw_vectors]
    weights = [0.0] * len(vectors[0])
    bias = statistics.mean(targets)
    lr = 0.025
    l2 = 0.001
    for _ in range(900):
        grad_w = [0.0] * len(weights)
        grad_b = 0.0
        for vec, target in zip(vectors, targets):
            pred = bias + sum(w * x for w, x in zip(weights, vec))
            error = pred - target
            for i, value in enumerate(vec):
                grad_w[i] += error * value
            grad_b += error
        n = max(len(vectors), 1)
        for i in range(len(weights)):
            weights[i] -= lr * ((grad_w[i] / n) + l2 * weights[i])
        bias -= lr * (grad_b / n)
    return {
        "algorithm": "standardized_log_linear_regression_gradient_descent",
        "feature_names": FEATURE_NAMES,
        "weights": weights,
        "bias": bias,
        "means": means,
        "stds": stds,
        "target_median": int(statistics.median(row["price_or_deposit_won"] for row in rows)),
    }


def predict(model: dict[str, Any], row: dict[str, Any]) -> float:
    if not model.get("weights"):
        return float(model.get("target_median", 0))
    vec = transform(feature_vector(row), model["means"], model["stds"])
    log_pred = model["bias"] + sum(w * x for w, x in zip(model["weights"], vec))
    return max(0.0, math.expm1(log_pred))


def evaluate(model: dict[str, Any], test_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not test_rows:
        return {"test_rows": 0}
    actuals = [float(row["price_or_deposit_won"]) for row in test_rows]
    preds = [predict(model, row) for row in test_rows]
    median = float(model.get("target_median", 0))
    baseline_preds = [median for _ in test_rows]

    def metrics(values: list[float]) -> dict[str, float]:
        errors = [pred - actual for pred, actual in zip(values, actuals)]
        abs_errors = [abs(error) for error in errors]
        squared_errors = [error * error for error in errors]
        mae = sum(abs_errors) / len(abs_errors)
        rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
        mape = sum(abs(pred - actual) / max(actual, 1.0) for pred, actual in zip(values, actuals)) / len(actuals)
        mean_actual = sum(actuals) / len(actuals)
        sst = sum((actual - mean_actual) ** 2 for actual in actuals)
        sse = sum((pred - actual) ** 2 for pred, actual in zip(values, actuals))
        r2 = 1 - sse / sst if sst else 0.0
        return {
            "mae_won": round(mae),
            "rmse_won": round(rmse),
            "mape": round(mape, 4),
            "r2": round(r2, 4),
        }

    return {
        "test_rows": len(test_rows),
        "model": metrics(preds),
        "median_baseline": metrics(baseline_preds),
    }


def train_by_trade_type(rows: list[dict[str, Any]], trade_type: str) -> dict[str, Any]:
    selected = [row for row in rows if row["trade_type"] == trade_type]
    train_rows, test_rows = train_test_split(selected)
    model = train_regressor(train_rows)
    return {
        "trade_type": trade_type,
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "model": model,
        "evaluation": evaluate(model, test_rows),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess market data, train MVP price models, and write evaluation artifacts.")
    parser.add_argument("--market-path", type=Path, default=DEFAULT_MARKET_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_rows = read_csv(args.market_path)
    processed = preprocess_market(raw_rows)
    rent_result = train_by_trade_type(processed, "전세")
    sale_result = train_by_trade_type(processed, "매매")
    eval_payload = {
        "task": "market_price_prediction",
        "data_preprocessing": [
            "UTF-8-SIG CSV ingestion",
            "housing_type normalization",
            "won and square-meter numeric conversion",
            "IQR clipping per legal_dong_code/housing_type/trade_type",
            "deterministic hash train/test split",
            "log-price regression for rent and sale price",
        ],
        "source_rows": len(raw_rows),
        "processed_rows": len(processed),
        "rent_model": {key: value for key, value in rent_result.items() if key != "model"},
        "sale_model": {key: value for key, value in sale_result.items() if key != "model"},
        "limitations": [
            "The included MVP market file is a compact contest demo dataset, so the evaluation is a reproducibility check rather than production accuracy.",
            "For production, replace the CSV with full recent 국토교통부 실거래가 API extracts and rerun this script.",
        ],
    }
    model_payload = {
        "rent_model": rent_result["model"],
        "sale_model": sale_result["model"],
    }
    write_csv(
        args.output_dir / "market_preprocessed.csv",
        processed,
        [
            "region",
            "legal_dong_code",
            "housing_type",
            "trade_type",
            "trade_month",
            "price_or_deposit_won",
            "monthly_rent_won",
            "exclusive_area_m2",
            "floor",
            "built_year",
            "normalized_basis",
            "outlier_clip_applied",
        ],
    )
    write_json(args.output_dir / "market_model_eval.json", eval_payload)
    write_json(args.output_dir / "market_model_weights.json", model_payload)
    print(json.dumps({
        "source_rows": len(raw_rows),
        "processed_rows": len(processed),
        "rent_test_rows": rent_result["test_rows"],
        "sale_test_rows": sale_result["test_rows"],
        "output_dir": str(args.output_dir),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
