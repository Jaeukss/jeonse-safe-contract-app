# Hugging Face Spaces 배포 메모

## 배포 방식

이 프로젝트는 Hugging Face Gradio Space로 배포한다. 루트 `README.md`의 YAML 블록에 `sdk: gradio`를 설정하고, `app_file`로 Python 진입점을 지정한다.

현재 설정:

```yaml
sdk: gradio
app_file: app.py
```

## 배포 전 확인

```powershell
node --check app/app.js
node --check src/risk-engine.js
node scripts/smoke-test.js
python -m compileall app.py backend
```

## 저장소에 포함되는 제출 자료

- 실행형 Gradio 앱: `app.py`
- 정적 포트폴리오 앱: `app/index.html`
- Python 모델 파이프라인: `backend/app/`
- 진단 엔진: `src/risk-engine.js`
- 백서: `docs/WHITEPAPER.md`
- 공식 RAG 출처: `data/rag_official_sources.json`
- 공식 링크표: `docs/OFFICIAL_RAG_SOURCE_LINKS.md`
- 데이터셋: `data/*.csv`, `data/*.json`, `data/xlsx/*.xlsx`
- 공공데이터 수집기: `scripts/collect_public_data.py`

## Hugging Face에 필요한 정보

배포를 완료하려면 다음 중 하나가 필요하다.

1. Hugging Face access token
2. 이미 생성된 Space의 git URL

권장 Space 이름:

```text
Jaeukss/jeonse-risk-diagnosis-agent
```

권장 공개 범위:

```text
Public
```

권장 SDK:

```text
Gradio
```
