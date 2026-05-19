from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContractInput(BaseModel):
    address: str
    legal_dong_code: str
    housing_type: str
    deposit_won: int = Field(ge=0)
    monthly_rent_won: int = Field(default=0, ge=0)
    exclusive_area_m2: float = Field(gt=0)
    floor: int | None = None
    built_year: int | None = None
    contract_stage: str = "계약 전 확인"
    document_text: str = ""
    registry_checked: bool = False
    building_checked: bool = False
    explanation_checked: bool = False
    senior_deposit_unknown: bool = False


class DiagnosisResponse(BaseModel):
    grade: str
    score: int
    confidence: str
    features: dict[str, Any]
    signals: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    actions: list[str]
    report_html: str
