# VSCode Evaluation Guide

## 목적

저장된 가격 예측 모델과 관악구/강서구 holdout 데이터를 사용해 모델 성능, 오차 상위 케이스, 세그먼트별 성능, 개선 모델 비교를 직접 확인한다.

## 기본 실행 순서

VSCode에서 프로젝트 폴더를 열고 터미널에서 실행한다.

```bash
python scripts/evaluate_price_model_errors.py
python scripts/segment_price_model_improvement.py
```

모델과 평가 데이터까지 다시 만들고 싶으면 아래 순서로 실행한다.

```bash
python scripts/benchmark_price_models.py
python scripts/evaluate_price_model_errors.py
python scripts/segment_price_model_improvement.py
```

## 입력 파일

- `data/models/best_price_model_seoul_multi_year.json`
- `data/processed/gwanak_gangseo_market_eval_scope_from_seoul_multi_year.csv`

위 파일이 없으면 `scripts/benchmark_price_models.py`를 먼저 실행한다.

## 오차 진단 출력

- `data/model_diagnostics/predictions_jeonse_deposit.csv`
- `data/model_diagnostics/predictions_sale_price.csv`
- `data/model_diagnostics/top_error_rate_10pct_*.csv`
- `data/model_diagnostics/top_error_rate_20pct_*.csv`
- `data/model_diagnostics/top_absolute_error_10pct_*.csv`
- `data/model_diagnostics/top_absolute_error_20pct_*.csv`
- `data/model_diagnostics/segment_performance_*.csv`
- `data/model_diagnostics/error_analysis_summary.json`
- `docs/MODEL_ERROR_ANALYSIS.md`

`predictions_*.csv`에는 아래 컬럼이 포함된다.

- `actual_value`: 실제값
- `predicted_value`: 예측값
- `absolute_error`: 절대오차
- `error_rate_percent`: 오차율

## 세그먼트 개선 실험 출력

- `data/models/segmented_price_model_summary.json`
- `data/model_improvements/segment_model_improvement_summary.json`
- `data/model_improvements/segment_improvement_predictions_jeonse_deposit.csv`
- `data/model_improvements/segment_improvement_predictions_sale_price.csv`
- `docs/SEGMENT_MODEL_IMPROVEMENT_REPORT.md`

개선 실험은 다음 후보를 비교한다.

- `baseline_seoul_hierarchical_median`: 서울 2년치 기반 기존 계층형 중앙값 모델
- `target_scope_segment_median`: 관악구/강서구 train 구간만 사용한 세그먼트 중앙값
- `segment_ratio_calibrated_baseline`: 세그먼트별 실제값/예측값 비율 보정
- `segment_residual_calibrated_baseline`: 세그먼트별 잔차 보정
- `routed_local_or_ratio`: 로컬 중앙값을 우선 사용하고 부족하면 비율 보정으로 fallback

## 해석 기준

- MAPE만 단독으로 보지 않는다. 저가 구간에서는 MAPE가 과장될 수 있으므로 MAE와 MdAPE를 함께 본다.
- 전세보증금과 매매가는 별도 모델로 해석한다.
- 전세 모델은 특정 케이스에서 크게 튀는 현상이 있어 오차 상위 파일과 세그먼트 성능표를 함께 본다.
- 개선 모델이 baseline보다 낮은 MdAPE/MAPE를 보일 때만 적용 후보로 둔다.
- 외부자료 없이 세그먼트 보정을 했는데 개선 폭이 작으면, 전세가격지수/금리/신규갱신 구분/입지 파생 데이터가 필요한 상태로 판단한다.
