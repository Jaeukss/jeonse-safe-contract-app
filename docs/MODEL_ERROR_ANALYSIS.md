# Model Error Analysis

작성일: 2026-05-21 03:11

## 실행 방법

```bash
python scripts/evaluate_price_model_errors.py
```

이 스크립트는 현재 저장된 다중연도 모델 파일과 관악구+강서구 holdout 평가 데이터를 사용한다.

## 전체 성능

| 대상             | 건수   | MAE         | MAPE   | MdAPE | 오차율 상위 10% 기준 |
| -------------- | ---- | ----------- | ------ | ----- | ------------- |
| jeonse_deposit | 8703 | 44,278,896원 | 23.17% | 9.09% | 46.67%        |
| sale_price     | 4821 | 64,462,850원 | 13.96% | 6.34% | 32.84%        |

## 오차가 큰 구간 Top 20

| target_kind    | segment_name | segment_value | rows | mae_won   | mape_percent | mdape_percent |
| -------------- | ------------ | ------------- | ---- | --------- | ------------ | ------------- |
| jeonse_deposit | 가격대          | 1억 미만         | 664  | 45943509  | 114.24       | 40.46         |
| jeonse_deposit | 주택유형         | 다가구           | 1246 | 45545273  | 51.38        | 27.27         |
| sale_price     | 가격대          | 1억 미만         | 99   | 36581717  | 49.02        | 7.14          |
| jeonse_deposit | 거래월          | 2025-07       | 327  | 43567997  | 43.55        | 9.09          |
| sale_price     | 주택유형         | 다가구           | 117  | 439106068 | 39.52        | 26.96         |
| jeonse_deposit | 거래월          | 2026-01       | 369  | 43568537  | 38.13        | 10.0          |
| jeonse_deposit | 법정동          | 관악구 봉천동       | 1540 | 43303445  | 35.77        | 9.16          |
| jeonse_deposit | 면적대          | 20㎡ 미만        | 740  | 19571318  | 35.3         | 6.94          |
| jeonse_deposit | 구            | 관악구           | 2855 | 41949518  | 33.14        | 10.26         |
| jeonse_deposit | 법정동          | 관악구 신림동       | 1203 | 38772049  | 30.6         | 11.61         |
| jeonse_deposit | 건축연한         | 11~20년        | 1915 | 60698420  | 30.48        | 11.76         |
| jeonse_deposit | 주택유형         | 연립다세대         | 1959 | 34883127  | 29.61        | 12.26         |
| jeonse_deposit | 법정동          | 강서구 공항동       | 145  | 37020552  | 28.74        | 14.5          |
| jeonse_deposit | 거래월          | 2024-09       | 296  | 45892838  | 26.65        | 9.26          |
| jeonse_deposit | 거래분기         | 2025Q3        | 964  | 41386266  | 26.45        | 8.0           |
| jeonse_deposit | 거래월          | 2024-05       | 241  | 37456328  | 25.77        | 8.15          |
| jeonse_deposit | 거래월          | 2025-12       | 316  | 45343655  | 25.75        | 8.43          |
| jeonse_deposit | 면적대          | 40~60㎡        | 2650 | 49488643  | 25.56        | 10.53         |
| jeonse_deposit | 거래월          | 2024-07       | 474  | 48052395  | 25.51        | 9.16          |
| sale_price     | 법정동          | 강서구 공항동       | 66   | 88982273  | 25.17        | 7.19          |

## 해석 원칙

- 오차율 상위 데이터는 `data/model_diagnostics/top_error_rate_*` 파일에서 확인한다.
- 고가 물건은 절대오차가 크고, 저가 물건은 MAPE가 과장될 수 있으므로 `top_absolute_error_*`도 함께 본다.
- 전세보증금 모델은 MAPE가 경고선을 넘었으므로 리포트에서는 참고 시세와 신뢰도 경고를 함께 표시한다.
- 건축연한은 원천 실거래가의 건축연도 값에 의존한다. 원천 결측 대체 여부는 별도 flag가 없으므로 해석 시 주의한다.

## 산출 파일

- `data\model_diagnostics\predictions_jeonse_deposit.csv`
- `data\model_diagnostics\top_error_rate_10pct_jeonse_deposit.csv`
- `data\model_diagnostics\top_absolute_error_10pct_jeonse_deposit.csv`
- `data\model_diagnostics\top_error_rate_20pct_jeonse_deposit.csv`
- `data\model_diagnostics\top_absolute_error_20pct_jeonse_deposit.csv`
- `data\model_diagnostics\segment_performance_jeonse_deposit.csv`
- `data\model_diagnostics\predictions_sale_price.csv`
- `data\model_diagnostics\top_error_rate_10pct_sale_price.csv`
- `data\model_diagnostics\top_absolute_error_10pct_sale_price.csv`
- `data\model_diagnostics\top_error_rate_20pct_sale_price.csv`
- `data\model_diagnostics\top_absolute_error_20pct_sale_price.csv`
- `data\model_diagnostics\segment_performance_sale_price.csv`
- `data\model_diagnostics\error_analysis_summary.json`
