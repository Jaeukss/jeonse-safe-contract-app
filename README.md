# 전세계약 안심진단

임차인이 전세계약 전에 보증금, 주택 정보, 등기부등본, 건축물대장, 계약서 특이사항을 한 번에 점검할 수 있도록 만든 Streamlit MVP입니다.

## Streamlit Cloud 설정

- Repository: `Jaeukss/jeonse-safe-contract-app`
- Branch: `main`
- Main file path: `app.py`

## 앱 기능

- 업로드하면 좋은 파일과 공식 발급 위치 안내
- 주소, 법정동코드, 주택유형, 보증금, 면적, 층, 건축연도 입력
- 등기부등본/건축물대장/계약서 PDF 또는 TXT 업로드
- 근저당권, 압류, 신탁등기, 위반건축물 등 위험 신호 추출
- 주변 시세와 예측 가격 기반 전세가율·시세괴리율 계산
- 위험등급, 위험 이유, 다음 행동, 공식 근거 링크 제공

## 공식 근거 데이터

앱 화면의 문서 안내와 공식 링크는 `data/tenant_action_guide.json`에 정리했습니다.

주요 근거:

- 대법원 인터넷등기소: `https://www.iros.go.kr/`
- 세움터: `https://www.eais.go.kr/`
- 법무부 자료실: `https://www.moj.go.kr/moj/315/subview.do`
- 모바일 HUG: `https://onestop.khug.or.kr/view/biz/apply/goods001`
- 주택임대차보호법: `https://www.law.go.kr/LSW/lsInfoP.do?lsId=001248`

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 폴더 구조

```text
app.py                      Streamlit 앱 진입점
backend/app/                진단 파이프라인, 위험 엔진, 문서 신호 추출
data/                       MVP 실행에 필요한 근거 데이터
docs/TENANT_APP_EVIDENCE.md 앱 화면 근거 설명
.streamlit/config.toml      Streamlit 공공기관형 밝은 테마
```
