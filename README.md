# 관악구 전세계약 위험진단 AI MVP

OCR이 틀리거나 문서가 없어도 체크박스 보완으로 위험진단까지 이어지는 관악구 데이터 기반 Streamlit 프로토타입입니다.

## 핵심 기능

- 관악구 전월세·매매 실거래가 전처리
- 관악구 건축물대장 전처리
- Raw Data Store: 사용자 입력, 체크박스, OCR, 공공데이터를 출처별 저장
- PDF/TXT/이미지 업로드 및 텍스트 추출
- 개인정보 마스킹
- 등기부등본·건축물대장·중개대상물 확인설명서 필드 추출
- 체크박스 기반 수동 보완
- OCR/체크박스/공공데이터 충돌 감지
- 진단 스냅샷 저장
- 유사 거래 검색과 가격 예측 fallback
- 전세가율·시세괴리율·시세 신뢰도 계산
- 위험 점수·등급 산출
- RAG 템플릿 설명과 Markdown 리포트 출력
- LangGraph 사용 가능 시 graph 빌드, 미설치 시 순차 workflow 실행

## 실행

```powershell
pip install -r requirements.txt
streamlit run app.py
```

현재 작업 환경에 Python이 PATH에 없다면 Codex 번들 Python 또는 로컬 Python 경로로 실행하세요.

## 데이터 전처리

```powershell
python src/preprocessing/clean_trade_data.py
python src/preprocessing/clean_building_data.py
```

산출물:

- `data/processed/ganak_rent_clean.csv`
- `data/processed/ganak_sale_clean.csv`
- `data/processed/ganak_building_clean.csv`

## 주요 구조

```text
app/main.py                         Streamlit 진입점
app/components/                     입력, 업로드, 체크박스, 충돌, 리포트 UI
src/input_layer/                    Raw Store, 병합, 충돌 감지, 스냅샷
src/document_ai/                    OCR 텍스트 추출, PII 마스킹, 문서 파서
src/modeling/                       유사 거래 검색, 가격 예측 fallback
src/risk/                           시세 지표, 권리관계 점수, 등급
src/rag/                            위험 신호 설명 템플릿과 근거 검색
src/agent/                          최소 Agent workflow
src/report/                         Markdown 리포트
tests/                              MVP 시나리오 테스트
docs/                               발표·사업계획서용 문서
```

## 테스트

```powershell
python scripts/run_mvp_smoke.py
pytest tests
```

## MVP 원칙

- OCR 정확도보다 입력 안정화 우선
- 공공데이터와 OCR이 충돌하면 사용자 확인
- 핵심 정보가 없으면 진단 신뢰도와 등급에 반영
- 법률 판단이 아니라 위험 신호 설명과 다음 행동 안내
