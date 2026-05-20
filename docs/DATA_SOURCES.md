# 데이터 소스 수집 설계

이 MVP는 발표와 스모크 테스트가 바로 가능하도록 seed 데이터를 포함한다. 실제 운영 또는 실증 단계에서는 아래 공식 출처에서 관악구 원천 데이터를 확보해 seed 파일을 교체해야 한다.

## 현재 포함된 데이터

- `data/market_transactions_mvp.csv`: 시연용 실거래가 seed 데이터
- `data/building_registry_mvp.csv`: 시연용 건축물대장 seed 데이터
- `data/rag_knowledge.json`: 위험 신호별 설명 템플릿
- `data/public_source_manifest.json`: 공식 출처, API endpoint, 인증 방식, MVP 사용처
- `docs/DATA_ACQUISITION_STATUS.md`: 확보 완료 출처와 남은 요청자료

## 공식 원천

1. [국토교통부 실거래가 공개시스템 자료제공](https://rt.molit.go.kr/pt/xls/xls.do?mobileAt=)
2. [국토교통부_실거래가 정보](https://www.data.go.kr/data/3050988/fileData.do)
3. [국토교통부_아파트 전월세 실거래가 자료](https://www.data.go.kr/data/15126474/openapi.do)
4. [국토교통부_아파트 매매 실거래가 자료](https://www.data.go.kr/data/15126469/openapi.do)
5. [국토교통부_연립다세대 전월세 실거래가 자료](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15126473)
6. [국토교통부_연립다세대 매매 실거래가 자료](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15126467)
7. [국토교통부_단독/다가구 전월세 실거래가 자료](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15126472)
8. [국토교통부_단독/다가구 매매 실거래가 자료](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15126465)
9. [국토교통부_오피스텔 전월세 실거래가 자료](https://www.data.go.kr/data/15126475/openapi.do)
10. [국토교통부_오피스텔 매매 실거래가 자료](https://www.data.go.kr/data/15126464/openapi.do)
11. [국토교통부_건축물대장정보 서비스](https://www.data.go.kr/dataset/15004825/openapi.do?lang=ko)
12. [행정표준코드관리시스템 법정동코드목록조회](https://www.code.go.kr/stdcode/regCodeL.do)
13. [국토교통부 전세계약 유의사항](https://www.molit.go.kr/USR/policyData/m_34681/dtl.jsp?id=4679)
14. [국토교통부 안전한 집](https://www.molit.go.kr/2023safehome/main.jsp)
15. [법무부 주택임대차표준](https://moj.go.kr/moj/314/subview.do)
16. [국가법령정보센터 주택임대차보호법](https://www.law.go.kr/lsInfoP.do?lsiSeq=183533)
17. [HUG 전세보증금반환보증 가입](https://onestop.khug.or.kr/webView/webBiz/apply/goods001)
18. [인터넷등기소](https://www.iros.go.kr/)
19. [정부24](https://www.gov.kr/)
20. [세움터](https://www.eais.go.kr/)

## 수집 방법

공공데이터포털 인증키를 발급받은 뒤 다음처럼 실행한다.

```powershell
$env:DATA_GO_KR_SERVICE_KEY="발급받은_인증키"
python scripts/collect_public_data.py --lawd-cd 11620 --months 202401 202402 202403
```

결과 저장 경로:

- 원문 XML: `data/raw/`
- 정규화 CSV: `data/processed/`

API 키가 없으면 국토교통부 실거래가 공개시스템에서 관악구 CSV를 직접 내려받아 `data/raw/trade/`에 넣고 전처리한다.

## 남은 자료

남은 자료는 [DATA_ACQUISITION_STATUS.md](./DATA_ACQUISITION_STATUS.md)의 "추가로 남은 요청자료"에만 정리했다.
