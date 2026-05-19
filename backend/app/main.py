from __future__ import annotations

from fastapi import FastAPI

from .pipeline import diagnose_contract
from .schemas import ContractInput, DiagnosisResponse


app = FastAPI(
    title="전세계약 안심진단 AI Agent API",
    version="1.0.0",
    description="공식 공공데이터와 RAG 근거 문서를 활용한 전세계약 위험 진단 API",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(payload: ContractInput) -> DiagnosisResponse:
    return diagnose_contract(payload)
