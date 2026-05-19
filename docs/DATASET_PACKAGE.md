# 데이터셋 패키지 설명

## 반영한 MVP 데이터셋

1. 사용자 입력 샘플 데이터
   - 파일: `data/user_input_samples.csv`
   - 반영 필드: 주소, 법정동코드, 주택유형, 전세보증금, 월세 여부, 월세, 전용면적, 층, 계약 단계

2. 실거래가 데이터
   - 파일: `data/market_transactions_mvp.csv`
   - 반영 필드: 지역명, 법정동코드, 주택유형, 거래유형, 거래년월, 거래가격 또는 보증금, 월세, 전용면적, 층, 건축연도
   - 활용: 전세가율, 시세괴리율, 적정 전세가, 추정 매매가, 유사거래 신뢰도

3. 건축물대장 데이터
   - 파일: `data/building_registry_mvp.csv`
   - 반영 필드: 주소, 도로명주소, 법정동코드, 건물명, 동명칭, 호명칭, 층, 주용도, 전유면적, 사용승인연도, 위반건축물 여부
   - 활용: 주택 용도, 면적, 사용승인연도, 위반건축물 위험 신호

4. RAG 문서 데이터
   - 파일: `data/rag_documents_mvp.json`
   - 공식 출처 파일: `data/rag_official_sources.json`
   - 제출용 링크표: `docs/OFFICIAL_RAG_SOURCE_LINKS.md`
   - 반영 문서: 주택임대차보호법, 시행령, 공인중개사법, 부동산등기법 안내, 건축물대장 안내, HUG 보증 안내, 국토교통부 전세사기 예방 체크리스트, 지자체 안내, 표준계약서, 중개대상물 확인설명서

## 전처리 기준

전처리 기준은 `data/preprocessing_rules.json`에 별도로 정리했다. 주소 표준화, 주택유형 통일, 금액 원 단위, 면적 m², 최근 1~2년 거래, 유사거래 묶음, 신뢰도 하향, 중앙값 기반 이상치 완화가 포함된다.

## 공식 원천

공식 원천은 `data/dataset_manifest.json`, `data/source_catalog.json`, `data/rag_official_sources.json`에 URL과 활용 위치로 정리했다. MVP에서는 인증키가 없어도 동작하도록 seed 데이터를 포함하고, 운영 단계에서는 같은 컬럼 구조로 공식 API 수집 데이터와 교체한다.

## Hugging Face 제출 패키지

배포본에 포함되는 앱, 백서, 데이터셋, RAG 출처, API 카탈로그 목록은 `data/submission_package.json`에서 한 번에 확인할 수 있다. 프로젝트 백서는 `docs/WHITEPAPER.md`에 별도로 정리했다.
