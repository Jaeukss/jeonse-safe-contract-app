from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from build_gwanak_gangseo_assets import predict_median


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data" / "models" / "best_price_model_seoul_multi_year.json"
EVAL_DATA_PATH = ROOT / "data" / "processed" / "gwanak_gangseo_market_eval_scope_from_seoul_multi_year.csv"
OUT_DIR = ROOT / "data" / "model_diagnostics"
REPORT_PATH = ROOT / "docs" / "MODEL_ERROR_ANALYSIS.md"

PRICE_BINS = [0, 100_000_000, 300_000_000, 500_000_000, math.inf]
PRICE_LABELS = ["1억 미만", "1~3억", "3~5억", "5억 이상"]
AREA_BINS = [0, 20, 40, 60, 85, math.inf]
AREA_LABELS = ["20㎡ 미만", "20~40㎡", "40~60㎡", "60~85㎡", "85㎡ 이상"]
AGE_BINS = [-1, 5, 10, 20, math.inf]
AGE_LABELS = ["5년 이하", "6~10년", "11~20년", "20년 초과"]


def require_file(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} 파일이 없습니다. {hint}")


def load_model_payload() -> dict[str, Any]:
    require_file(
        MODEL_PATH,
        "먼저 `python scripts/benchmark_price_models.py`를 실행해 모델 파일을 생성하세요.",
    )
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def load_eval_data() -> pd.DataFrame:
    require_file(
        EVAL_DATA_PATH,
        "먼저 `python scripts/benchmark_price_models.py`를 실행해 평가 데이터 파일을 생성하세요.",
    )
    df = pd.read_csv(EVAL_DATA_PATH)
    if "is_target_scope" in df:
        df = df[df["is_target_scope"].astype(str).str.lower().isin(["true", "1"])]
    if "split" in df:
        df = df[df["split"].eq("test")]
    return df.copy()


def safe_mape(actual: pd.Series, pred: pd.Series) -> float:
    actual = pd.to_numeric(actual, errors="coerce")
    pred = pd.to_numeric(pred, errors="coerce")
    mask = actual.gt(0) & pred.notna()
    if not mask.any():
        return 0.0
    return float(((pred[mask] - actual[mask]).abs() / actual[mask]).mean() * 100)


def safe_mdape(actual: pd.Series, pred: pd.Series) -> float:
    actual = pd.to_numeric(actual, errors="coerce")
    pred = pd.to_numeric(pred, errors="coerce")
    mask = actual.gt(0) & pred.notna()
    if not mask.any():
        return 0.0
    return float(((pred[mask] - actual[mask]).abs() / actual[mask]).median() * 100)


def safe_mae(actual: pd.Series, pred: pd.Series) -> float:
    actual = pd.to_numeric(actual, errors="coerce")
    pred = pd.to_numeric(pred, errors="coerce")
    mask = actual.notna() & pred.notna()
    if not mask.any():
        return 0.0
    return float((pred[mask] - actual[mask]).abs().mean())


def safe_rmse(actual: pd.Series, pred: pd.Series) -> float:
    actual = pd.to_numeric(actual, errors="coerce")
    pred = pd.to_numeric(pred, errors="coerce")
    mask = actual.notna() & pred.notna()
    if not mask.any():
        return 0.0
    return float(((pred[mask] - actual[mask]) ** 2).mean() ** 0.5)


def performance_row(target_kind: str, segment_name: str, segment_value: str, df: pd.DataFrame) -> dict[str, Any]:
    return {
        "target_kind": target_kind,
        "segment_name": segment_name,
        "segment_value": segment_value,
        "rows": int(len(df)),
        "actual_median_won": int(round(pd.to_numeric(df["actual_value"], errors="coerce").median())) if len(df) else 0,
        "prediction_median_won": int(round(pd.to_numeric(df["predicted_value"], errors="coerce").median())) if len(df) else 0,
        "mae_won": int(round(safe_mae(df["actual_value"], df["predicted_value"]))),
        "rmse_won": int(round(safe_rmse(df["actual_value"], df["predicted_value"]))),
        "mape_percent": round(safe_mape(df["actual_value"], df["predicted_value"]), 2),
        "mdape_percent": round(safe_mdape(df["actual_value"], df["predicted_value"]), 2),
    }


def add_segments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_range"] = pd.cut(df["actual_value"], bins=PRICE_BINS, labels=PRICE_LABELS, right=False)
    df["area_range"] = pd.cut(pd.to_numeric(df["area_m2"], errors="coerce"), bins=AREA_BINS, labels=AREA_LABELS, right=False)
    built_year = pd.to_numeric(df["built_year"], errors="coerce")
    df["building_age"] = (2026 - built_year).where(built_year.gt(0))
    df["building_age_range"] = pd.cut(df["building_age"], bins=AGE_BINS, labels=AGE_LABELS, right=True)
    ym = pd.to_datetime(df["transaction_ym"].astype(str) + "-01", errors="coerce")
    df["transaction_month"] = ym.dt.strftime("%Y-%m").fillna("미상")
    df["transaction_quarter"] = ym.dt.to_period("Q").astype(str).replace("NaT", "미상")
    df["district_dong"] = df["district"].astype(str) + " " + df["dong"].astype(str)
    return df


def predict_target(eval_df: pd.DataFrame, model_payload: dict[str, Any], target_kind: str) -> pd.DataFrame:
    if target_kind not in model_payload:
        raise KeyError(f"{MODEL_PATH}에 {target_kind} 모델이 없습니다.")
    tables = model_payload[target_kind]["model_payload"]["tables"]
    df = eval_df[eval_df["target_kind"].eq(target_kind)].copy()
    df["actual_value"] = pd.to_numeric(df["target_won"], errors="coerce")
    df["predicted_value"] = [float(predict_median(row, tables)) for _, row in df.iterrows()]
    df["absolute_error"] = (df["actual_value"] - df["predicted_value"]).abs()
    df["error_rate_percent"] = df["absolute_error"] / df["actual_value"].clip(lower=1) * 100
    df = add_segments(df)
    return df.sort_values("error_rate_percent", ascending=False).reset_index(drop=True)


def save_top_errors(target_kind: str, predictions: pd.DataFrame) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    base_cols = [
        "district",
        "dong",
        "housing_type",
        "transaction_ym",
        "building_name",
        "road_name",
        "lot_no",
        "area_m2",
        "floor",
        "built_year",
        "actual_value",
        "predicted_value",
        "absolute_error",
        "error_rate_percent",
    ]
    for rate in [0.10, 0.20]:
        n = max(1, math.ceil(len(predictions) * rate))
        percent = int(rate * 100)
        for sort_col, label in [("error_rate_percent", "error_rate"), ("absolute_error", "absolute_error")]:
            output = OUT_DIR / f"top_{label}_{percent}pct_{target_kind}.csv"
            predictions.sort_values(sort_col, ascending=False).head(n)[base_cols].to_csv(output, index=False, encoding="utf-8-sig")
            saved.append({"target_kind": target_kind, "kind": label, "percent": percent, "rows": n, "path": str(output.relative_to(ROOT))})
    return saved


def build_segment_table(target_kind: str, predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = [performance_row(target_kind, "overall", "전체", predictions)]
    segment_specs = {
        "housing_type": "주택유형",
        "price_range": "가격대",
        "area_range": "면적대",
        "building_age_range": "건축연한",
        "transaction_month": "거래월",
        "transaction_quarter": "거래분기",
        "district": "구",
        "district_dong": "법정동",
    }
    for col, label in segment_specs.items():
        for value, group in predictions.groupby(col, dropna=False, observed=False):
            value_label = "미상" if pd.isna(value) else str(value)
            rows.append(performance_row(target_kind, label, value_label, group))
    table = pd.DataFrame(rows)
    return table.sort_values(["target_kind", "segment_name", "mape_percent", "rows"], ascending=[True, True, False, False])


def top_segment_findings(segment_table: pd.DataFrame, min_rows: int = 30) -> pd.DataFrame:
    filtered = segment_table[(segment_table["segment_name"].ne("overall")) & (segment_table["rows"] >= min_rows)].copy()
    return filtered.sort_values(["mape_percent", "mae_won"], ascending=False).head(20)


def format_won(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}원"
    except (TypeError, ValueError):
        return "0원"


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
    if df.empty:
        return "결과 없음\n"
    view = df.head(limit)[columns].copy()
    rows = [[str(value) for value in row] for row in view.to_numpy().tolist()]
    headers = [str(col) for col in columns]
    widths = [
        max(len(headers[idx]), *(len(row[idx]) for row in rows))
        for idx in range(len(headers))
    ]
    header_line = "| " + " | ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers))) + " |"
    sep_line = "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |"
    body_lines = [
        "| " + " | ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line, *body_lines])


def build_report(summary: dict[str, Any], segment_tables: list[pd.DataFrame]) -> str:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Model Error Analysis",
        "",
        f"작성일: {created_at}",
        "",
        "## 실행 방법",
        "",
        "```bash",
        "python scripts/evaluate_price_model_errors.py",
        "```",
        "",
        "이 스크립트는 현재 저장된 다중연도 모델 파일과 관악구+강서구 holdout 평가 데이터를 사용한다.",
        "",
        "## 전체 성능",
        "",
    ]
    overall_rows = []
    for item in summary["targets"]:
        overall_rows.append(
            {
                "대상": item["target_kind"],
                "건수": item["rows"],
                "MAE": format_won(item["mae_won"]),
                "MAPE": f"{item['mape_percent']}%",
                "MdAPE": f"{item['mdape_percent']}%",
                "오차율 상위 10% 기준": f"{item['top_error_rate_10pct_threshold']}%",
            }
        )
    lines.append(markdown_table(pd.DataFrame(overall_rows), ["대상", "건수", "MAE", "MAPE", "MdAPE", "오차율 상위 10% 기준"]))
    lines.extend(["", "## 오차가 큰 구간 Top 20", ""])
    combined_segments = pd.concat(segment_tables, ignore_index=True)
    findings = top_segment_findings(combined_segments)
    lines.append(markdown_table(findings, ["target_kind", "segment_name", "segment_value", "rows", "mae_won", "mape_percent", "mdape_percent"]))
    lines.extend(
        [
            "",
            "## 해석 원칙",
            "",
            "- 오차율 상위 데이터는 `data/model_diagnostics/top_error_rate_*` 파일에서 확인한다.",
            "- 고가 물건은 절대오차가 크고, 저가 물건은 MAPE가 과장될 수 있으므로 `top_absolute_error_*`도 함께 본다.",
            "- 전세보증금 모델은 MAPE가 경고선을 넘었으므로 리포트에서는 참고 시세와 신뢰도 경고를 함께 표시한다.",
            "- 건축연한은 원천 실거래가의 건축연도 값에 의존한다. 원천 결측 대체 여부는 별도 flag가 없으므로 해석 시 주의한다.",
            "",
            "## 산출 파일",
            "",
        ]
    )
    for path in summary["output_files"]:
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_payload = load_model_payload()
    eval_df = load_eval_data()

    summary: dict[str, Any] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model_path": str(MODEL_PATH.relative_to(ROOT)),
        "eval_data_path": str(EVAL_DATA_PATH.relative_to(ROOT)),
        "targets": [],
        "output_files": [],
    }
    segment_tables: list[pd.DataFrame] = []

    for target_kind in ["jeonse_deposit", "sale_price"]:
        predictions = predict_target(eval_df, model_payload, target_kind)
        prediction_path = OUT_DIR / f"predictions_{target_kind}.csv"
        predictions.to_csv(prediction_path, index=False, encoding="utf-8-sig")
        summary["output_files"].append(str(prediction_path.relative_to(ROOT)))

        top_files = save_top_errors(target_kind, predictions)
        summary["output_files"].extend(item["path"] for item in top_files)

        segment_table = build_segment_table(target_kind, predictions)
        segment_path = OUT_DIR / f"segment_performance_{target_kind}.csv"
        segment_table.to_csv(segment_path, index=False, encoding="utf-8-sig")
        summary["output_files"].append(str(segment_path.relative_to(ROOT)))
        segment_tables.append(segment_table)

        top_10_threshold = float(predictions["error_rate_percent"].quantile(0.90))
        summary["targets"].append(
            {
                "target_kind": target_kind,
                "rows": int(len(predictions)),
                "mae_won": int(round(safe_mae(predictions["actual_value"], predictions["predicted_value"]))),
                "rmse_won": int(round(safe_rmse(predictions["actual_value"], predictions["predicted_value"]))),
                "mape_percent": round(safe_mape(predictions["actual_value"], predictions["predicted_value"]), 2),
                "mdape_percent": round(safe_mdape(predictions["actual_value"], predictions["predicted_value"]), 2),
                "top_error_rate_10pct_threshold": round(top_10_threshold, 2),
            }
        )

    summary_path = OUT_DIR / "error_analysis_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["output_files"].append(str(summary_path.relative_to(ROOT)))

    report = build_report(summary, segment_tables)
    REPORT_PATH.write_text(report, encoding="utf-8")
    summary["output_files"].append(str(REPORT_PATH.relative_to(ROOT)))
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
