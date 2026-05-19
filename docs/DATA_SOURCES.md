# 데이터 수집 설계

이 MVP에는 앱에서 즉시 실행 가능한 seed 데이터와, 실제 공공데이터를 수집하기 위한 원천 카탈로그·수집기가 함께 들어 있다.

## 현재 담긴 데이터

- `data/seed_market.csv`: 실거래가 API 구조에 맞춘 시연용 전월세·매매 데이터
- `data/seed_building_registry.csv`: 건축물대장 표제부 구조에 맞춘 시연용 건축물 데이터
- `data/rag_knowledge.json`: 위험 신호별 설명 근거
- `data/source_catalog.json`: 공식 원천, API endpoint, 인증 방식, 주요 필드, MVP 활용 위치
- `data/rag_official_sources.json`: RAG 문서 데이터 10종의 공식 출처, 확인일, MVP 활용 목적

## 공식 원천

1. 국토교통부 실거래가 공개시스템 및 공공데이터포털 RTMS API
2. 국토교통부 건축물대장 표제부 API
3. 법제처 국가법령정보센터 주택임대차보호법·시행령
4. HUG 전세보증금반환보증 상품 안내
5. 법무부 주택임대차 표준계약서
6. 정부24 건축물대장 등본·초본 발급·열람 안내
7. 서울주거포털 전세사기 피해 예방·지원 안내
8. 행정표준코드관리시스템 법정동코드

## 수집 방법

공공데이터포털 인증키를 발급한 뒤 다음처럼 실행한다.

```powershell
$env:DATA_GO_KR_SERVICE_KEY="발급받은_인증키"
python scripts/collect_public_data.py --lawd-cd 11500 --months 202511 202512
```

결과는 다음 경로에 저장된다.

- 원문 XML: `data/raw/`
- 정규화 CSV: `data/processed/`

## 왜 seed 데이터도 포함하는가

공식 API는 무료지만 공공데이터포털 활용신청과 인증키가 필요하다. 심사 환경에서 인증키 없이도 인앱 데모와 LAG 체인을 검증할 수 있도록 seed 데이터를 포함했고, 실제 배포 시에는 수집기로 원천 데이터를 교체한다.

## 제출 시 같이 제시할 파일

- 공식 RAG 링크표: `docs/OFFICIAL_RAG_SOURCE_LINKS.md`
- RAG 출처 원장: `data/rag_official_sources.json`
- 데이터셋 매니페스트: `data/dataset_manifest.json`
