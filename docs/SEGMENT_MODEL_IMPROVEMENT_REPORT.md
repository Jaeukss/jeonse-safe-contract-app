# Segment Model Improvement Report

작성일: 2026-05-21T03:32:21

## 목적

전세보증금 예측에서 저가 구간, 다가구, 일부 법정동/월 구간의 오차가 크게 튀는 문제를 확인했기 때문에, 외부자료 없이 현재 실거래 데이터만으로 가능한 1차 개선을 실험했다.

## 방법

- 기존 서울 2년치 기반 계층형 유사거래 중앙값 모델을 baseline으로 사용했다.
- 관악구/강서구 train 구간에서 주택유형, 법정동, 면적대, 예측 가격대, 거래월, 건축연한별 보정값을 학습했다.
- 후보 모델은 baseline, 대상지역 세그먼트 중앙값, 비율 보정, 잔차 보정, 로컬 중앙값/비율 보정 라우팅 모델로 비교했다.
- holdout test 구간에서 MAE, RMSE, MAPE, MdAPE를 비교했다.

## 성능 비교

### jeonse_deposit
| model                                | MAE         | RMSE        | MAPE   | MdAPE |
| ------------------------------------ | ----------- | ----------- | ------ | ----- |
| baseline_seoul_hierarchical_median   | 44,278,896원 | 71,759,288원 | 23.17% | 9.09% |
| target_scope_segment_median          | 46,292,527원 | 73,337,055원 | 24.23% | 10.0% |
| segment_ratio_calibrated_baseline    | 44,206,259원 | 71,357,277원 | 23.14% | 9.09% |
| segment_residual_calibrated_baseline | 44,205,317원 | 71,379,371원 | 23.14% | 9.09% |
| routed_local_or_ratio                | 46,292,527원 | 73,337,055원 | 24.23% | 10.0% |

선택 모델: `segment_residual_calibrated_baseline`
baseline 대비 개선: MAE 73,579원, MAPE 0.03%p, MdAPE 0.0%p

### sale_price
| model                                | MAE         | RMSE         | MAPE   | MdAPE |
| ------------------------------------ | ----------- | ------------ | ------ | ----- |
| baseline_seoul_hierarchical_median   | 64,462,850원 | 145,187,818원 | 13.96% | 6.34% |
| target_scope_segment_median          | 79,569,955원 | 162,774,581원 | 17.3%  | 8.21% |
| segment_ratio_calibrated_baseline    | 64,464,089원 | 145,190,001원 | 13.96% | 6.34% |
| segment_residual_calibrated_baseline | 64,464,250원 | 145,188,070원 | 13.96% | 6.34% |
| routed_local_or_ratio                | 79,569,955원 | 162,774,581원 | 17.3%  | 8.21% |

선택 모델: `baseline_seoul_hierarchical_median`
baseline 대비 개선: MAE 0원, MAPE 0.0%p, MdAPE 0.0%p

## 적용 판단

- 전세보증금은 특정 세그먼트에서 튀는 문제가 있으므로, 단일 전체 모델보다 세그먼트 보정/라우팅 모델을 우선 적용 후보로 둔다.
- 매매가는 baseline이 충분히 안정적이면 무리하게 보정하지 않고, 개선 모델이 명확히 낮은 MdAPE/MAPE를 보일 때만 선택한다.
- 현재 개선은 외부 전세가격지수, 금리, 신규/갱신 구분, 역세권 거리 없이 수행한 1차 개선이다.

## 추가자료 없이 가능한 범위

- 주택유형별 분리, 저가 구간 보정, 법정동/월/면적대 보정은 현재 데이터만으로 가능하다.
- 다만 전세 모델의 구조적 오차를 더 줄이려면 전세가격지수, 금리, 신규/갱신 구분, 입지 파생 데이터가 필요하다.

## 산출물

- `data\model_improvements\segment_model_improvement_summary.json`
- `data\models\segmented_price_model_summary.json`
- `data\model_improvements\segment_improvement_predictions_jeonse_deposit.csv`
- `data\model_improvements\segment_improvement_predictions_sale_price.csv`
