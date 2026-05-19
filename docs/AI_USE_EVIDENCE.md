# AI 활용 및 데이터 사용 증빙 메모

참고 이미지의 심사 안내처럼 AI 도구와 데이터 활용 사실을 증빙할 수 있도록 제출 패키지에 다음 자료를 포함한다.

## AI 활용 증빙

- 실행형 Gradio 앱: `app.py`
- 정적 포트폴리오 화면: `app/index.html`
- AI 위험 진단 로직: `src/risk-engine.js`
- 프로젝트 백서: `docs/WHITEPAPER.md`
- RAG 문서 데이터: `data/rag_documents_mvp.json`
- RAG 공식 출처 원장: `data/rag_official_sources.json`
- RAG 제출용 링크표: `docs/OFFICIAL_RAG_SOURCE_LINKS.md`
- 진단 처리 흐름 설명: `docs/LAG_CHAIN.md`
- 자동 검증 스크립트: `scripts/smoke-test.js`

## 데이터셋 증빙

- 사용자 입력 샘플: `data/user_input_samples.csv`
- 실거래가 시연 데이터: `data/market_transactions_mvp.csv`
- 건축물대장 시연 데이터: `data/building_registry_mvp.csv`
- 전처리 원칙: `data/preprocessing_rules.json`
- 데이터 목록표: `data/dataset_manifest.json`
- 공식 원천 카탈로그: `data/source_catalog.json`
- RAG 공식 출처 링크: `data/rag_official_sources.json`
- 제출 패키지 매니페스트: `data/submission_package.json`

## 데이터 안심구역 또는 주관기관 융합 활용 시 보완 자료

실제 데이터 안심구역을 이용하게 되면 이용신청 내역, 방문자 관리대장, 반출 승인 내역을 추가로 제출하면 된다. 현재 MVP는 공개 가능한 seed 데이터와 공식 API 원천 URL을 기반으로 구성되어 있어 별도 반출 심사 없이 시연 가능하다.
