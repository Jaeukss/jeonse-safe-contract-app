# 전세계약 위험진단 AI MVP

OCR 텍스트를 먼저 추출하고, 추출 실패 또는 불확실 항목은 사용자 수기 입력·선택지 입력으로 보완해 진단까지 이어지는 관악구+강서구 데이터 기반 Streamlit 프로토타입입니다.

## 핵심 기능

- 데이터 입력 전 문서 준비 안내, 계약 전 행동 체크, 보증금 조정 시뮬레이터
- 일반 임차인용 쉬운 설명 모드와 공인중개사/컨설턴트용 근거 중심 모드
- 관악구+강서구 전월세·매매 실거래가 전처리
- 관악구+강서구 건축물대장 전처리
- Raw Data Store: 기본 입력, OCR 결과, 사용자 보완 입력, 공공데이터를 출처별 저장
- PDF/TXT/이미지 업로드 및 OCR 텍스트 추출
- 개인정보 마스킹
- 등기부등본·건축물대장·중개대상물 확인설명서 핵심 필드 추출
- OCR 결과 확인 및 사용자 보완 입력
- OCR/사용자 보완 입력/공공데이터 충돌 감지
- 진단 스냅샷 저장
- 유사 거래 검색과 가격 예측 fallback
- 전세가율·시세괴리율·시세 신뢰도 계산
- 위험 점수·등급 산출
- RAG 템플릿 설명과 Markdown 리포트 출력
- LangGraph 사용 가능 시 graph 빌드, 미설치 시 절차형 workflow 실행

## 실행

```powershell
pip install -r requirements.txt
python scripts/bootstrap_data.py
streamlit run app.py
```

Python이 PATH에 없다면 로컬 Python 또는 Codex 번들 Python 경로로 실행하세요.

## OpenRouter 설정

LLM 기반 문서 JSON 보정은 OpenRouter API key가 있을 때만 활성화됩니다. 배포자가 설정해야 하는 값은 `OPENROUTER_API_KEY` 하나입니다.

Streamlit Cloud 또는 `.streamlit/secrets.toml`:

```toml
OPENROUTER_API_KEY = "sk-or-..."
```

로컬 환경변수:

```powershell
$env:OPENROUTER_API_KEY="sk-or-..."
streamlit run app.py
```

기본 호출 모델은 `nvidia/nemotron-3-super-120b-a12b:free` 단일 모델입니다. API key가 없거나 호출에 실패하면 기존 규칙 기반 OCR/텍스트 추출과 사용자 보완 입력 흐름만 사용합니다. 임베딩 또는 벡터DB 검색 키가 별도로 필요한 구조를 추가할 경우에는 이 키와 분리해서 관리해야 합니다.

## 데이터 적용 방식

앱은 시작할 때 `src/data_bootstrap.py`로 전처리 데이터 상태를 확인합니다.

- 로컬에 `artifacts/gwanak_gangseo_final_used_files.zip`이 있으면 필요한 CSV/RAG/모델 산출물을 자동으로 풉니다.
- 배포 환경에서는 `JEONSE_DATA_ZIP_URL` 환경변수에 zip 다운로드 URL을 넣으면 앱이 시작 시 내려받아 풉니다.
- 자동 준비를 끄고 싶으면 `JEONSE_AUTO_BOOTSTRAP=0`을 설정합니다.

VSCode에서 전체 데이터가 적용됐는지 먼저 확인하려면 아래만 실행해도 됩니다.

```powershell
python scripts/bootstrap_data.py
python scripts/run_mvp_smoke.py
```

## 데이터 전처리

```powershell
python src/preprocessing/clean_trade_data.py
python src/preprocessing/clean_building_data.py
```

주요 산출물:

- `data/processed/gwanak_gangseo_rent_clean.csv`
- `data/processed/gwanak_gangseo_sale_clean.csv`
- `data/processed/gwanak_gangseo_building_title_clean.csv`
- `data/processed/gwanak_gangseo_official_house_price_latest.csv`

## 주요 구조

```text
app/main.py                         Streamlit 진입점
app/components/                     기본 입력, 문서 업로드, OCR 결과 확인/보완, 충돌, 리포트 UI
src/input_layer/                    Raw Store, 병합, 충돌 감지, 스냅샷
src/document_ai/                    OCR 텍스트 추출, PII 마스킹, 문서 파서
src/modeling/                       유사 거래 검색, 가격 예측 fallback
src/risk/                           시세 지표, 권리관계 점수, 위험등급
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

- 예전 UI/UX의 장점인 문서 준비 안내와 쉬운 진행 순서는 유지한다.
- OCR 정확도보다 입력 안정화를 우선한다.
- OCR 추출 실패·불확실 항목은 사용자 수기 입력 또는 선택지 입력으로 보완한다.
- 공공데이터와 OCR이 충돌하면 바로 덮어쓰지 않고 사용자 확인을 거친다.
- 주소 매칭이 불확실한 공공 건축물대장 값은 진단 필드로 강제 반영하지 않는다.
- 법률 판단이 아니라 위험 신호 설명과 다음 행동 안내를 제공한다.

## 포지셔닝

HUG/KB가 결과형 전세안전진단에 가깝다면, 이 MVP는 OCR 오류·서류 누락·입력 충돌까지 감안해 사용자가 계약 전 확인해야 할 정보를 끝까지 정리하는 증거 기반 전세계약 위험진단 AI Agent입니다.
