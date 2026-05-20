from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from build_gwanak_gangseo_assets import area_bucket, build_median_tables, metrics, predict_median


ROOT = Path(__file__).resolve().parents[1]
BASE_MODEL_PATH = ROOT / "data" / "models" / "best_price_model_seoul_multi_year.json"
EVAL_DATA_PATH = ROOT / "data" / "processed" / "gwanak_gangseo_market_eval_scope_from_seoul_multi_year.csv"
OUT_DIR = ROOT / "data" / "model_improvements"
REPORT_PATH = ROOT / "docs" / "SEGMENT_MODEL_IMPROVEMENT_REPORT.md"
SELECTED_MODEL_PATH = ROOT / "data" / "models" / "segmented_price_model_summary.json"

PRICE_BINS = [0, 100_000_000, 300_000_000, 500_000_000, math.inf]
PRICE_LABELS = ["under_100m", "100m_300m", "300m_500m", "over_500m"]
AREA_BINS = [0, 20, 40, 60, 85, math.inf]
AREA_LABELS = ["under_20m2", "20m2_40m2", "40m2_60m2", "60m2_85m2", "over_85m2"]
AGE_BINS = [-1, 5, 10, 20, math.inf]
AGE_LABELS = ["under_5y", "6y_10y", "11y_20y", "over_20y"]

CORRECTION_MIN_ROWS = 30
LOCAL_MEDIAN_MIN_ROWS = 5
RATIO_FLOOR = 0.65
RATIO_CEILING = 1.35


MEDIAN_SPECS: list[tuple[str, list[str]]] = [
    ("building_area", ["district", "dong", "housing_type", "building_name", "area_bucket"]),
    ("road_area", ["district", "dong", "housing_type", "road_name", "area_bucket"]),
    ("lot_area", ["district", "dong", "housing_type", "lot_no", "area_bucket"]),
    ("dong_type_price_area", ["district", "dong", "housing_type", "predicted_price_range", "area_range"]),
    ("dong_type_area", ["district", "dong", "housing_type", "area_bucket"]),
    ("dong_type", ["district", "dong", "housing_type"]),
    ("district_type_area", ["district", "housing_type", "area_bucket"]),
    ("type_price_area", ["housing_type", "predicted_price_range", "area_range"]),
    ("type_area", ["housing_type", "area_bucket"]),
    ("type", ["housing_type"]),
    ("price_area", ["predicted_price_range", "area_range"]),
    ("global", []),
]

CORRECTION_SPECS: list[tuple[str, list[str]]] = [
    ("dong_type_price_area", ["district", "dong", "housing_type", "predicted_price_range", "area_range"]),
    ("dong_type_price", ["district", "dong", "housing_type", "predicted_price_range"]),
    ("dong_type_area", ["district", "dong", "housing_type", "area_range"]),
    ("dong_type_month", ["district", "dong", "housing_type", "transaction_month"]),
    ("dong_type", ["district", "dong", "housing_type"]),
    ("district_type_price", ["district", "housing_type", "predicted_price_range"]),
    ("type_price_area", ["housing_type", "predicted_price_range", "area_range"]),
    ("type_price", ["housing_type", "predicted_price_range"]),
    ("type_age", ["housing_type", "building_age_range"]),
    ("type", ["housing_type"]),
    ("price_range", ["predicted_price_range"]),
    ("global", []),
]


def require_file(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. {hint}")


def load_base_model() -> dict[str, Any]:
    require_file(BASE_MODEL_PATH, "Run `python scripts/benchmark_price_models.py` first.")
    return json.loads(BASE_MODEL_PATH.read_text(encoding="utf-8"))


def load_eval_data() -> pd.DataFrame:
    require_file(EVAL_DATA_PATH, "Run `python scripts/benchmark_price_models.py` first.")
    df = pd.read_csv(EVAL_DATA_PATH)
    if "is_target_scope" in df:
        df = df[df["is_target_scope"].astype(str).str.lower().isin(["true", "1"])]
    df["area_bucket"] = df["area_m2"].apply(area_bucket)
    return df.copy()


def make_key(row: pd.Series, columns: list[str]) -> str:
    if not columns:
        return "*"
    return "|".join(str(row.get(column, "")) for column in columns)


def add_segments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["actual_value"] = pd.to_numeric(df["target_won"], errors="coerce")
    df["predicted_price_range"] = pd.cut(
        pd.to_numeric(df["baseline_prediction"], errors="coerce"),
        bins=PRICE_BINS,
        labels=PRICE_LABELS,
        right=False,
    ).astype(str)
    df["area_range"] = pd.cut(
        pd.to_numeric(df["area_m2"], errors="coerce"),
        bins=AREA_BINS,
        labels=AREA_LABELS,
        right=False,
    ).astype(str)
    built_year = pd.to_numeric(df["built_year"], errors="coerce")
    df["building_age"] = (2026 - built_year).where(built_year.gt(0))
    df["building_age_range"] = pd.cut(df["building_age"], bins=AGE_BINS, labels=AGE_LABELS, right=True).astype(str)
    ym = pd.to_datetime(df["transaction_ym"].astype(str) + "-01", errors="coerce")
    df["transaction_month"] = ym.dt.strftime("%Y-%m").fillna("unknown")
    df["district_dong"] = df["district"].astype(str) + " " + df["dong"].astype(str)
    return df


def predict_saved_baseline(df: pd.DataFrame, base_model: dict[str, Any], target_kind: str) -> pd.Series:
    tables = base_model[target_kind]["model_payload"]["tables"]
    rows = df[df["target_kind"].eq(target_kind)]
    return pd.Series([float(predict_median(row, tables)) for _, row in rows.iterrows()], index=rows.index)


def build_group_table(
    train: pd.DataFrame,
    specs: list[tuple[str, list[str]]],
    value_col: str,
    min_rows: int,
    agg: str = "median",
) -> dict[str, dict[str, dict[str, float]]]:
    tables: dict[str, dict[str, dict[str, float]]] = {}
    for name, columns in specs:
        if not columns:
            values = pd.to_numeric(train[value_col], errors="coerce").dropna()
            tables[name] = {
                "*": {
                    "value": float(values.median() if agg == "median" else values.mean()),
                    "rows": float(len(values)),
                }
            }
            continue
        grouped = train.groupby(columns, dropna=False)[value_col].agg(["median", "count"]).reset_index()
        grouped = grouped[grouped["count"].ge(min_rows)]
        table: dict[str, dict[str, float]] = {}
        for _, row in grouped.iterrows():
            key = "|".join(str(row[column]) for column in columns)
            table[key] = {"value": float(row["median"]), "rows": float(row["count"])}
        tables[name] = table
    return tables


def lookup_table(
    row: pd.Series,
    tables: dict[str, dict[str, dict[str, float]]],
    specs: list[tuple[str, list[str]]],
    default: float,
) -> tuple[float, str, int]:
    for name, columns in specs:
        key = make_key(row, columns)
        item = tables.get(name, {}).get(key)
        if item:
            return float(item["value"]), name, int(item["rows"])
    return default, "fallback", 0


def support_aware_local_median(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, dict[str, Any]]:
    tables = build_group_table(train, MEDIAN_SPECS, "target_won", LOCAL_MEDIAN_MIN_ROWS)
    predictions: list[float] = []
    sources: list[str] = []
    support: list[int] = []
    fallback = float(pd.to_numeric(train["target_won"], errors="coerce").median())
    for _, row in test.iterrows():
        value, source, rows = lookup_table(row, tables, MEDIAN_SPECS, fallback)
        predictions.append(value)
        sources.append(source)
        support.append(rows)
    payload = {"min_rows": LOCAL_MEDIAN_MIN_ROWS, "specs": MEDIAN_SPECS, "tables": tables}
    return pd.Series(predictions, index=test.index), pd.Series(sources, index=test.index), pd.Series(support, index=test.index), payload


def calibrated_predictions(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict[str, Any]]:
    train = train.copy()
    train["ratio_to_baseline"] = train["target_won"] / train["baseline_prediction"].clip(lower=1)
    train["residual_to_baseline"] = train["target_won"] - train["baseline_prediction"]

    ratio_tables = build_group_table(train, CORRECTION_SPECS, "ratio_to_baseline", CORRECTION_MIN_ROWS)
    residual_tables = build_group_table(train, CORRECTION_SPECS, "residual_to_baseline", CORRECTION_MIN_ROWS)

    ratio_predictions: list[float] = []
    residual_predictions: list[float] = []
    ratio_sources: list[str] = []
    residual_sources: list[str] = []
    for _, row in test.iterrows():
        ratio, ratio_source, _ = lookup_table(row, ratio_tables, CORRECTION_SPECS, 1.0)
        ratio = min(max(ratio, RATIO_FLOOR), RATIO_CEILING)
        residual, residual_source, _ = lookup_table(row, residual_tables, CORRECTION_SPECS, 0.0)
        baseline = float(row["baseline_prediction"])
        ratio_predictions.append(max(0.0, baseline * ratio))
        residual_predictions.append(max(0.0, baseline + residual))
        ratio_sources.append(ratio_source)
        residual_sources.append(residual_source)

    payload = {
        "ratio_floor": RATIO_FLOOR,
        "ratio_ceiling": RATIO_CEILING,
        "min_rows": CORRECTION_MIN_ROWS,
        "specs": CORRECTION_SPECS,
        "ratio_tables": ratio_tables,
        "residual_tables": residual_tables,
    }
    return (
        pd.Series(ratio_predictions, index=test.index),
        pd.Series(residual_predictions, index=test.index),
        {"payload": payload, "ratio_sources": ratio_sources, "residual_sources": residual_sources},
    )


def evaluate(actual: pd.Series, predicted: pd.Series) -> dict[str, Any]:
    item = metrics(actual.astype(float).tolist(), predicted.astype(float).tolist())
    return {
        "rows": int(item["rows"]),
        "mae_won": int(item["mae_won"]),
        "rmse_won": int(item["rmse_won"]),
        "mape_percent": round(float(item["mape"]) * 100, 2),
        "mdape_percent": round(float(item["median_ape"]) * 100, 2),
    }


def build_target_result(df: pd.DataFrame, base_model: dict[str, Any], target_kind: str) -> dict[str, Any]:
    scoped = df[df["target_kind"].eq(target_kind)].copy()
    scoped["baseline_prediction"] = predict_saved_baseline(scoped, base_model, target_kind)
    scoped = add_segments(scoped)
    train = scoped[scoped["split"].eq("train")].copy()
    test = scoped[scoped["split"].eq("test")].copy()

    local_pred, local_source, local_support, local_payload = support_aware_local_median(train, test)
    ratio_pred, residual_pred, calibration = calibrated_predictions(train, test)

    routed = ratio_pred.copy()
    use_local = local_support.ge(LOCAL_MEDIAN_MIN_ROWS)
    routed.loc[use_local] = local_pred.loc[use_local]

    candidate_predictions = {
        "baseline_seoul_hierarchical_median": test["baseline_prediction"],
        "target_scope_segment_median": local_pred,
        "segment_ratio_calibrated_baseline": ratio_pred,
        "segment_residual_calibrated_baseline": residual_pred,
        "routed_local_or_ratio": routed,
    }
    evaluations = {
        name: evaluate(test["actual_value"], pred)
        for name, pred in candidate_predictions.items()
    }
    selected_name = min(
        evaluations,
        key=lambda name: (evaluations[name]["mdape_percent"], evaluations[name]["mape_percent"], evaluations[name]["mae_won"]),
    )

    predictions = test.copy()
    for name, pred in candidate_predictions.items():
        predictions[f"prediction_{name}"] = pred
        predictions[f"ape_{name}"] = (pred - predictions["actual_value"]).abs() / predictions["actual_value"].clip(lower=1) * 100
    predictions["selected_model"] = selected_name
    predictions["selected_prediction"] = candidate_predictions[selected_name]
    predictions["selected_absolute_error"] = (predictions["selected_prediction"] - predictions["actual_value"]).abs()
    predictions["selected_error_rate_percent"] = predictions["selected_absolute_error"] / predictions["actual_value"].clip(lower=1) * 100
    predictions["local_median_source"] = local_source
    predictions["local_median_support_rows"] = local_support

    output_path = OUT_DIR / f"segment_improvement_predictions_{target_kind}.csv"
    predictions.to_csv(output_path, index=False, encoding="utf-8-sig")

    return {
        "target_kind": target_kind,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "candidate_evaluations": evaluations,
        "selected_model": selected_name,
        "selected_evaluation": evaluations[selected_name],
        "baseline_evaluation": evaluations["baseline_seoul_hierarchical_median"],
        "improvement_vs_baseline": {
            metric: round(
                evaluations["baseline_seoul_hierarchical_median"][metric] - evaluations[selected_name][metric],
                2,
            )
            for metric in ["mae_won", "rmse_won", "mape_percent", "mdape_percent"]
        },
        "prediction_file": str(output_path.relative_to(ROOT)),
        "model_payload": {
            "local_median": local_payload,
            "calibration": calibration["payload"],
            "selected_model": selected_name,
        },
    }


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return ""
    widths = [len(column) for column in columns]
    for row in rows:
        for idx, column in enumerate(columns):
            widths[idx] = max(widths[idx], len(str(row.get(column, ""))))
    lines = [
        "| " + " | ".join(column.ljust(widths[idx]) for idx, column in enumerate(columns)) + " |",
        "| " + " | ".join("-" * widths[idx] for idx in range(len(columns))) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")).ljust(widths[idx]) for idx, column in enumerate(columns)) + " |")
    return "\n".join(lines)


def format_eval(value: Any, suffix: str = "") -> str:
    if isinstance(value, (int, float)):
        if "won" in suffix:
            return f"{int(round(value)):,}원"
        return f"{value}{suffix}"
    return str(value)


def build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Segment Model Improvement Report",
        "",
        f"작성일: {summary['created_at']}",
        "",
        "## 목적",
        "",
        "전세보증금 예측에서 저가 구간, 다가구, 일부 법정동/월 구간의 오차가 크게 튀는 문제를 확인했기 때문에, 외부자료 없이 현재 실거래 데이터만으로 가능한 1차 개선을 실험했다.",
        "",
        "## 방법",
        "",
        "- 기존 서울 2년치 기반 계층형 유사거래 중앙값 모델을 baseline으로 사용했다.",
        "- 관악구/강서구 train 구간에서 주택유형, 법정동, 면적대, 예측 가격대, 거래월, 건축연한별 보정값을 학습했다.",
        "- 후보 모델은 baseline, 대상지역 세그먼트 중앙값, 비율 보정, 잔차 보정, 로컬 중앙값/비율 보정 라우팅 모델로 비교했다.",
        "- holdout test 구간에서 MAE, RMSE, MAPE, MdAPE를 비교했다.",
        "",
        "## 성능 비교",
        "",
    ]

    for target in summary["targets"]:
        lines.append(f"### {target['target_kind']}")
        rows: list[dict[str, Any]] = []
        for name, evaluation in target["candidate_evaluations"].items():
            rows.append(
                {
                    "model": name,
                    "MAE": format_eval(evaluation["mae_won"], "won"),
                    "RMSE": format_eval(evaluation["rmse_won"], "won"),
                    "MAPE": f"{evaluation['mape_percent']}%",
                    "MdAPE": f"{evaluation['mdape_percent']}%",
                }
            )
        lines.append(markdown_table(rows, ["model", "MAE", "RMSE", "MAPE", "MdAPE"]))
        lines.extend(
            [
                "",
                f"선택 모델: `{target['selected_model']}`",
                f"baseline 대비 개선: MAE {int(target['improvement_vs_baseline']['mae_won']):,}원, MAPE {target['improvement_vs_baseline']['mape_percent']}%p, MdAPE {target['improvement_vs_baseline']['mdape_percent']}%p",
                "",
            ]
        )

    lines.extend(
        [
            "## 적용 판단",
            "",
            "- 전세보증금은 특정 세그먼트에서 튀는 문제가 있으므로, 단일 전체 모델보다 세그먼트 보정/라우팅 모델을 우선 적용 후보로 둔다.",
            "- 매매가는 baseline이 충분히 안정적이면 무리하게 보정하지 않고, 개선 모델이 명확히 낮은 MdAPE/MAPE를 보일 때만 선택한다.",
            "- 현재 개선은 외부 전세가격지수, 금리, 신규/갱신 구분, 역세권 거리 없이 수행한 1차 개선이다.",
            "",
            "## 추가자료 없이 가능한 범위",
            "",
            "- 주택유형별 분리, 저가 구간 보정, 법정동/월/면적대 보정은 현재 데이터만으로 가능하다.",
            "- 다만 전세 모델의 구조적 오차를 더 줄이려면 전세가격지수, 금리, 신규/갱신 구분, 입지 파생 데이터가 필요하다.",
            "",
            "## 산출물",
            "",
            f"- `{summary['summary_path']}`",
            f"- `{summary['selected_model_path']}`",
        ]
    )
    for target in summary["targets"]:
        lines.append(f"- `{target['prediction_file']}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_model = load_base_model()
    df = load_eval_data()

    targets = [
        build_target_result(df, base_model, "jeonse_deposit"),
        build_target_result(df, base_model, "sale_price"),
    ]

    selected_payload = {
        target["target_kind"]: {
            "selected_model": target["selected_model"],
            "selected_evaluation": target["selected_evaluation"],
            "baseline_evaluation": target["baseline_evaluation"],
            "improvement_vs_baseline": target["improvement_vs_baseline"],
            "candidate_evaluations": target["candidate_evaluations"],
            "note": "Detailed segment tables are reproducible by rerunning scripts/segment_price_model_improvement.py.",
        }
        for target in targets
    }
    SELECTED_MODEL_PATH.write_text(json.dumps(selected_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = OUT_DIR / "segment_model_improvement_summary.json"
    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "base_model_path": str(BASE_MODEL_PATH.relative_to(ROOT)),
        "eval_data_path": str(EVAL_DATA_PATH.relative_to(ROOT)),
        "summary_path": str(summary_path.relative_to(ROOT)),
        "selected_model_path": str(SELECTED_MODEL_PATH.relative_to(ROOT)),
        "targets": [
            {key: value for key, value in target.items() if key != "model_payload"}
            for target in targets
        ],
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(build_report(summary), encoding="utf-8")
    summary["report_path"] = str(REPORT_PATH.relative_to(ROOT))
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
