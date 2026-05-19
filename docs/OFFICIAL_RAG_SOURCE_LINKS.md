# 공식 RAG 문서 출처 링크

이 문서는 MVP의 RAG 문서 데이터가 어떤 공식 자료를 근거로 구성됐는지 심사용으로 설명하는 링크표다. 원문 전체를 복제하지 않고 공식 URL, 활용 목적, RAG 매핑 항목을 보존한다.

## 4-4 RAG 문서 데이터

| 구분 | 공식 자료 | 제공기관 | 공식 링크 | MVP 활용 |
| --- | --- | --- | --- | --- |
| 1 | 주택임대차보호법 | 법제처 국가법령정보센터 | https://www.law.go.kr/LSW/lsInfoP.do?lsId=001248 | 대항력, 확정일자, 우선변제권, 보증금 보호 설명 |
| 2 | 주택임대차보호법 시행령 | 법제처 국가법령정보센터 | https://www.law.go.kr/법령/주택임대차보호법시행령 | 소액임차인 보호 범위, 보증금 규모별 확인 안내 |
| 3 | 공인중개사법 | 법제처 국가법령정보센터 | https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=273341 | 중개대상물 확인·설명 의무, 설명자료 요구 안내 |
| 4 | 부동산등기법 | 법제처 국가법령정보센터 | https://www.law.go.kr/법령/부동산등기법 | 근저당권, 압류, 가압류, 신탁등기 위험 설명 |
| 5 | 건축물대장 등본·초본 발급·열람 안내 | 정부24 | https://m.gov.kr/mw/AA020InfoCappView.do?CappBizCD=15000000098&HighCtgCD=A09005&tp_seq=01 | 주용도, 면적, 사용승인일, 위반건축물 여부 확인 |
| 6 | 전세보증금반환보증 상품 안내 | HUG 주택도시보증공사 | https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp | 보증한도, 보증조건, 선순위채권 확인 안내 |
| 7 | 전세사기 예방 안전한 집 | 국토교통부 | https://www.molit.go.kr/2023safehome/main.jsp | 계약 전·계약 당일·잔금 전 체크리스트 구성 |
| 8 | 전세사기피해자등 결정신청 및 예방 안내 | 서울특별시 서울주거포털 | https://housing.seoul.go.kr/site/main/content/sh05_070100 | 지자체 상담센터, 피해 예방·지원 절차 안내 |
| 9 | 주택임대차 표준계약서 | 법무부 | https://moj.go.kr/moj/314/subview.do | 특약, 보증금 반환, 관리비, 권리보장 조항 안내 |
| 10 | 중개대상물 확인·설명서 서식 근거 | 법제처 국가법령정보센터 | https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joNo=0016&lsiSeq=263573&urlMode=lsScJoRltInfoR | 확인설명서 필수 항목, 주거용 건축물 서식 근거 |

## 보조 다운로드 링크

| 자료 | 링크 | 비고 |
| --- | --- | --- |
| 국토교통부 전세계약 유의사항 리플렛 | https://www.molit.go.kr/portal/common/download/DownloadMltm2.jsp?FileName=%EC%A0%84%EC%84%B8%EA%B3%84%EC%95%BD+%EC%9C%A0%EC%9D%98%EC%82%AC%ED%95%AD+%EB%A6%AC%ED%94%8C%EB%A0%9B.pdf&FilePath=portal%2FDextUpload%2F202301%2F20230113_090421_309.pdf | 계약 전 확인사항 리플렛 |
| 서울시 전세사기 예방 A to Z PDF | https://housing.seoul.go.kr/design/theme/housing/images/sub/sh05_070100/%EC%A0%84%EC%84%B8%20%EA%B3%84%EC%95%BD.%20%EB%91%90%EB%A0%B5%EC%A7%80%20%EC%95%8A%EC%95%84%EC%9A%94%20%EC%A0%84%EC%84%B8%20%EC%82%AC%EA%B8%B0%20%EC%98%88%EB%B0%A9%20A%20to%20Z.pdf | 지자체 예방 안내서 |
| 모바일 HUG 전세보증금반환보증 신청 안내 | https://onestop.khug.or.kr/view/biz/apply/goods001 | 보증 신청 화면 및 제출서류 안내 |
| 주택임대차 표준계약서 자료실 | https://www.moj.go.kr/moj/315/subview.do | 법무부 다운로드 게시판 |

## 데이터셋 공식 원천

| 데이터셋 | 공식 링크 | MVP 활용 |
| --- | --- | --- |
| 국토교통부 아파트 전월세 실거래가 자료 | https://www.data.go.kr/data/15126474/openapi.do | 전세 시세 비교 |
| 국토교통부 아파트 매매 실거래가 자료 | https://www.data.go.kr/data/15126469/openapi.do | 추정 매매가와 전세가율 계산 |
| 국토교통부 오피스텔 전월세 실거래가 자료 | https://www.data.go.kr/data/15126475/openapi.do | 오피스텔 전세 시세 비교 |
| 국토교통부 오피스텔 매매 실거래가 자료 | https://www.data.go.kr/data/15126464/openapi.do | 오피스텔 추정 매매가 계산 |
| 국토교통부 실거래가 정보 파일데이터 | https://www.data.go.kr/data/3050988/fileData.do | CSV 다운로드 기반 운영 데이터 교체 |
| 국토교통부 건축물대장 정보 서비스 | https://www.data.go.kr/dataset/15004825/openapi.do | 건축물대장 표제부, 전유부, 층별개요 수집 |

## 로컬 파일

- RAG 요약 인덱스: `data/rag_documents_mvp.json`
- 공식 출처 원장: `data/rag_official_sources.json`
- 전체 데이터셋 목록: `data/dataset_manifest.json`
- 공공데이터 API 카탈로그: `data/source_catalog.json`
