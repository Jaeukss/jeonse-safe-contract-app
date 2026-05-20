# VSCode Evaluation Guide

## 목적

현재 저장된 모델과 관악구+강서구 holdout 데이터를 사용해 가격 예측 성능과 오차 원인을 직접 확인한다.

## 실행 순서

VSCode에서 프로젝트 폴더를 열고 터미널에서 실행한다.

```bash
python scripts/evaluate_price_model_errors.py
```

모델과 평가 데이터까지 다시 만들고 싶으면 먼저 아래를 실행한다.

```bash
python scripts/benchmark_price_models.py
python scripts/evaluate_price_model_errors.py
```

## 입력 파일

- `data/models/best_price_model_seoul_multi_year.json`
- `data/processed/gwanak_gangseo_market_eval_scope_from_seoul_multi_year.csv`

위 파일이 없으면 `scripts/benchmark_price_models.py`를 먼저 실행한다.

## 출력 파일

- `data/model_diagnostics/predictions_jeonse_deposit.csv`
- `data/model_diagnostics/predictions_sale_price.csv`
- `data/model_diagnostics/top_error_rate_10pct_*.csv`
- `data/model_diagnostics/top_error_rate_20pct_*.csv`
- `data/model_diagnostics/top_absolute_error_10pct_*.csv`
- `data/model_diagnostics/top_absolute_error_20pct_*.csv`
- `data/model_diagnostics/segment_performance_*.csv`
- `data/model_diagnostics/error_analysis_summary.json`
- `docs/MODEL_ERROR_ANALYSIS.md`

## 확인할 컬럼

`predictions_*.csv`에는 아래 컬럼이 포함된다.

- `actual_value`: 실제값
- `predicted_value`: 예측값
- `absolute_error`: 절대오차
- `error_rate_percent`: 오차율

## 해석 기준

- MAPE만 단독으로 보지 않는다.
- 저가 구간은 MAPE가 과장될 수 있으므로 MAE와 MdAPE를 같이 본다.
- 전세보증금과 매매가는 별도로 해석한다.
- 오차율 상위 파일과 절대오차 상위 파일을 함께 본다.
- 특정 주택유형, 가격대, 면적대, 건축연한, 거래월, 법정동에서만 오차가 크면 해당 구간용 모델 분리 또는 파생 변수를 검토한다.
