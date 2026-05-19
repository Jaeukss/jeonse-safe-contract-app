# 기술 구현 설계

이 문서는 전세계약 안심진단 AI Agent의 실제 Hugging Face 실행 구성과 확장 설계를 함께 설명한다. 현재 배포본은 Gradio/Python 기반으로 동작하며, PyTorch MLP 가격 예측, Pandas 시세 비교, 문서 신호 추출, RAG 근거 검색, 조건 분기 Agent가 Space 안에서 실제 실행된다. 기존 `app/index.html`은 정적 포트폴리오 화면으로 함께 보관한다.

## 기능별 구현

| 기능 | Model/기술 | 구현 |
| --- | --- | --- |
| 1. 사용자 입력 및 주소 정규화 | Python, FastAPI, 주소 정규화 로직, 법정동코드 매핑 | 주소·주택유형·금액·면적 입력 → 원 단위·㎡ 단위·표준 주택유형으로 정규화 → 필수값 누락 검증 |
| 2. 주변 시세 비교 | Pandas, NumPy, Scikit-learn, IQR/Z-score 이상치 완화 | 같은 법정동·주택유형·면적·건축연도 기준 유사 거래군 생성 → 중앙값·최솟값·최댓값·유사 거래 건수 산출 |
| 3. 적정 전세가 예측 | MLP Regressor, PyTorch, Tabular DL | 지역·주택유형·전용면적·층·건축연도·주변 시세를 입력해 `predicted_rent_price` 산출 |
| 4. 추정 매매가 예측 | MLP Regressor, PyTorch | 전세가율 계산을 위한 `predicted_sale_price` 산출 → 사용자 보증금과 비교 |
| 5. 위험 피처 생성 | Rule Engine, Python | `jeonse_ratio`, `rent_gap_rate`, `similar_transaction_count`, `mortgage_flag`, `trust_flag` 등 위험 피처 생성 |
| 6. 문서 AI | OCR, PDF text extraction, Regex, LLM 후처리, 추후 LayoutLMv3 | 등기부등본·건축물대장·계약서에서 근저당권, 채권최고액, 압류, 신탁등기, 위반건축물 여부 추출 |
| 7. RAG 설명 | Sentence Embedding, PostgreSQL+pgvector 또는 Chroma, LLM | 주택임대차보호법, HUG 안내, 전세사기 예방 체크리스트를 검색해 위험 사유와 다음 행동 설명 |
| 8. LangGraph Agent | LangGraph, StateGraph, Conditional Edge | 다가구·신탁등기·압류·유사거래 부족 등 조건에 따라 진단 흐름 분기 |
| 9. 최종 리포트 생성 | LLM Template, HTML/PDF/DOCX Export | 위험등급, 신뢰도, 위험 사유, 확인 문서, 다음 행동을 리포트 형태로 제공 |

## 현재 Hugging Face 배포 구성

| 영역 | 현재 구현 | 확장 가능성 |
| --- | --- | --- |
| 배포 | Hugging Face Gradio Space | Docker Space, Cloud Run, EC2, GPU Space |
| UI | `app.py` Gradio 실행 앱 + `app/index.html` 정적 포트폴리오 | React/Vue 프론트엔드와 FastAPI 분리 |
| 진단 엔진 | Python rule engine | 룰 버전관리, A/B threshold 실험 |
| 예측 모델 | PyTorch MLP Regressor 런타임 학습·추론 | 모델 레지스트리, 배치 재학습, MLflow |
| 시세 비교 | Pandas/NumPy 유사거래군 + IQR 완화 | 대용량 DB, 지역별 인덱싱, 실시간 API 수집 |
| 문서 추출 | PDF text extraction + Regex | OCR, LLM 후처리, LayoutLMv3 |
| RAG | 공식 URL + 요약 chunk 검색 | sentence-transformers + pgvector 또는 Chroma |
| Agent | 조건 분기 route 실행 | LangGraph StateGraph 전환 |
| 리포트 | Gradio HTML/JSON 리포트 | PDF/DOCX 다운로드, 전자문서 보관 |

## 코드 구조

```text
app.py                        Hugging Face Gradio entrypoint
backend/
  requirements.txt
  app/
    main.py                   FastAPI endpoint
    schemas.py                request/response schema
    pipeline.py               end-to-end diagnosis pipeline
    address.py                주소·주택유형·단위 정규화
    market.py                 유사거래군, IQR/Z-score 완화, 시세 통계
    models.py                 PyTorch MLP regressor train/inference
    risk.py                   위험 피처와 등급 산출
    document_ai.py            PDF/OCR/Regex/LLM 후처리 인터페이스
    rag.py                    공식 근거 문서 검색
    agent.py                  LangGraph 전환 가능한 조건 분기 설계
    report.py                 HTML/PDF/DOCX 리포트 생성 인터페이스
```

## 확장 설계 원칙

1. **모델 교체 가능성**: 현재 MLP는 `backend/app/models.py`에 격리되어 있어 XGBoost, TabNet, FT-Transformer 등으로 교체할 수 있다.
2. **RAG 저장소 교체 가능성**: 현재 JSON chunk 검색은 `backend/app/rag.py`에서 담당하며, 같은 인터페이스로 Chroma 또는 pgvector 검색기로 바꿀 수 있다.
3. **Agent 분기 확장성**: 현재 조건 분기는 `backend/app/agent.py`의 route 리스트로 실행되며, 운영 단계에서 LangGraph StateGraph로 옮길 수 있다.
4. **문서 AI 확장성**: Regex 추출은 `backend/app/document_ai.py`에 격리되어 있어 OCR, LLM 후처리, LayoutLMv3를 단계적으로 추가할 수 있다.
5. **공공데이터 교체성**: seed CSV와 공식 API 수집 데이터는 같은 컬럼 구조를 사용해 `data/processed/` 결과로 교체 가능하다.
