# End-to-End MVP Pipeline

이 문서는 제출용 저장소에서 데이터 전처리, RAG 문서 구축, 모델 학습, 성능평가, 앱 실행까지 재현하는 기준 절차를 정리한다.

## 1. 데이터 역할 구분

### 공식문서 RAG 데이터

위험 진단 결과를 설명하고 다음 행동을 제안하는 근거 문서이다.

- 국토교통부 전세계약 유의사항 리플렛
- 서울시 전세사기 예방 A to Z PDF
- HUG 전세보증금반환보증 신청 안내
- 주택임대차 표준계약서
- 주택임대차보호법 및 시행령
- 공인중개사법
- 부동산등기법 안내
- 건축물대장 확인 안내
- 중개대상물 확인설명서 양식

생성 코드:

```powershell
python scripts/rag_document_pipeline.py
```

출력:

- `data/rag/official_rag_corpus.jsonl`
- `data/rag/official_rag_manifest.json`
- `data/rag/official_rag_retrieval_eval.json`

현재 평가 결과:

- 문서 수: 10
- chunk 수: 10
- RAG 검색 `hit@5`: 1.0

주의: 저장소에는 저작권이 있는 PDF 원문 전체를 복사하지 않고, 공식 URL, 출처 메타데이터, MVP용 요약 chunk, 검색 평가 결과를 저장한다.

## 2. 구조화 공공데이터 전처리

실거래가와 건축물대장은 RAG 문서가 아니라 모델 피처와 검증 근거에 사용하는 구조화 데이터이다.

### 건축물대장 ZIP

사용자가 제공한 10개 ZIP을 사용한다.

- 서울/인천/경기 표제부
- 서울/인천/경기 전유부
- 서울/인천/경기 층별개요
- 서울 전유공용면적

생성 코드:

```powershell
python scripts/registry_pipeline.py --input-dir "$env:USERPROFILE\Downloads" --max-rows-per-zip 800 --max-rows-per-file 80
```

출력:

- `data/registry/registry_records_sample.csv`
- `data/registry/registry_feature_table.csv`
- `data/registry/registry_search_chunks.jsonl`
- `data/registry/registry_ingestion_manifest.json`
- `data/registry/registry_model_eval.json`
- `data/registry/registry_model_weights.json`

현재 처리 결과:

- 원본 ZIP 수: 10
- 샘플링된 원천 행: 8,000
- 정규화 피처 행: 5,018
- 구조화 검색 chunk: 5,018
- 약지도 분류 F1: 0.9953
- 구조화 검색 `recall@5`: 0.66

주의: 제공된 건축물대장 CSV 샘플 헤더에서는 `위반건축물 여부` 컬럼이 직접 확인되지 않았다. 따라서 이 값을 임의 추정하지 않고 `violation_status=unknown`으로 보존한다.

## 3. 시세 모델 학습 및 평가

실거래가 CSV를 전처리하고 전세/매매 가격 예측 모델을 학습한다.

생성 코드:

```powershell
python scripts/train_evaluate_models.py
```

출력:

- `data/models/market_preprocessed.csv`
- `data/models/market_model_eval.json`
- `data/models/market_model_weights.json`

전처리 절차:

1. UTF-8-SIG CSV 로딩
2. 주택유형 표준화
3. 금액 원 단위 변환
4. 면적 제곱미터 단위 변환
5. 법정동코드/주택유형/거래유형별 IQR 이상치 완화
6. 결정적 해시 기반 train/test split
7. log-price 회귀 모델 학습

현재 평가 결과:

- 실거래가 원천 행: 21
- 전처리 후 행: 21
- 전세 테스트 행: 1
- 매매 테스트 행: 1

이 값은 MVP 코드 재현성 확인용이다. 실제 성능평가로 제출하려면 국토교통부 실거래가 API에서 최근 1~2년 거래를 추가 수집해야 한다.

## 4. 전체 파이프라인 한 번에 실행

```powershell
python scripts/run_full_pipeline.py
```

건축물대장 ZIP이 없는 환경에서 공식문서 RAG와 시세 모델만 재생성하려면:

```powershell
python scripts/run_full_pipeline.py --skip-registry
```

## 5. 실거래가 API 데이터 확장

대회 제출용 실제 성능평가를 위해서는 data.go.kr 서비스키가 필요하다.

```powershell
$env:DATA_GO_KR_SERVICE_KEY="발급받은_서비스키"
python scripts/collect_public_data.py --lawd-cd 11500 --months 202501 202502 202503
python scripts/train_evaluate_models.py --market-path data/processed/rtms_11500_202501_202503.csv
```

수집 대상은 `data/source_catalog.json`에 정리되어 있다.

## 6. 앱 실행

Hugging Face Spaces와 동일한 Gradio 진입점은 루트 `app.py`이다.

```powershell
pip install -r requirements.txt
python app.py
```

앱 내부 진단 흐름:

1. 사용자 입력 및 주소/주택유형 정규화
2. 문서 텍스트에서 근저당, 압류, 신탁, 위반건축물 신호 추출
3. 주변 실거래가 비교
4. 가격 예측 모델 실행
5. 위험 피처 생성
6. 조건 분기 Agent 실행
7. 공식문서 RAG 근거 검색
8. HTML/JSON 진단 리포트 생성

## 7. 확장 설계

- 공식문서 RAG: 현재 JSONL 기반 검색에서 Chroma 또는 PostgreSQL pgvector로 교체 가능
- 가격 예측: 현재 MVP 회귀/Gradio 내 PyTorch MLP에서 대용량 실거래가 기반 Tabular DL로 확장 가능
- 문서 AI: 현재 Regex/PDF text extraction에서 OCR/LayoutLMv3로 확장 가능
- Agent: 현재 조건 분기 모듈에서 LangGraph `StateGraph`로 확장 가능
- 평가: 현재 재현성 평가에서 실제 사고/보증 거절/권리침해 라벨 기반 평가로 확장 가능
