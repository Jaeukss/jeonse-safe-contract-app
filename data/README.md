# MVP 데이터셋 패키지

이 폴더는 전세계약 위험 진단 AI Agent MVP에서 사용하는 제출용 데이터셋과 RAG 문서 데이터를 담는다.

## 제공 파일

- `user_input_samples.csv`: 사용자 입력 샘플 데이터
- `market_transactions_mvp.csv`: 실거래가 시연 데이터
- `building_registry_mvp.csv`: 건축물대장 시연 데이터
- `rag_documents_mvp.json`: RAG 근거 문서 데이터
- `rag_official_sources.json`: RAG 근거 문서 10종의 공식 출처 링크와 활용 목적
- `preprocessing_rules.json`: 데이터 전처리 원칙
- `dataset_manifest.json`: 제출 파일 목록과 공식 원천 URL
- `seed_market.csv`, `seed_building_registry.csv`, `rag_knowledge.json`: 앱 엔진과 직접 맞물리는 seed 파일
- `source_catalog.json`: 실제 공공데이터 수집 시 교체할 원천 카탈로그
- `submission_package.json`: Hugging Face 배포본에 포함되는 앱, 데이터셋, 문서, API 자료 목록
- `../docs/OFFICIAL_RAG_SOURCE_LINKS.md`: 사람이 읽기 쉬운 제출용 공식 링크표
- `../docs/WHITEPAPER.md`: 프로젝트 백서

## 운영 전환 방식

공공데이터포털 인증키를 발급받으면 `scripts/collect_public_data.py`로 원천 XML을 수집하고 `data/processed/`에 정규화 CSV를 저장한다. MVP에서는 심사 환경에서 인증키 없이도 작동하도록 seed 데이터를 함께 제공한다.
