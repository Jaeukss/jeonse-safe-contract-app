# Backend Extension Skeleton

이 폴더는 현재 Static MVP를 운영형 AI Agent로 확장할 때 사용할 FastAPI/Python 구조다. Hugging Face Static Space 배포에는 필요하지 않지만, GitHub 포트폴리오에서 모델·RAG·LangGraph 확장 설계를 확인할 수 있도록 포함했다.

## 실행 예시

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## 주요 API

- `GET /health`: 상태 확인
- `POST /diagnose`: 사용자 입력, 문서 텍스트, 위험 체크값을 받아 진단 리포트 생성

## 구현 범위

- 주소·주택유형·금액·면적 정규화
- Pandas/NumPy 기반 유사 거래군 산출
- IQR 기반 이상치 완화
- PyTorch MLP Regressor 인터페이스
- Regex 기반 문서 위험 신호 추출
- RAG 검색 인터페이스
- LangGraph 조건 분기 설계
- HTML/PDF/DOCX 리포트 생성 인터페이스
