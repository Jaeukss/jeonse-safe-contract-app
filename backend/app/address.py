from __future__ import annotations

from dataclasses import dataclass

from .schemas import ContractInput


HOUSING_TYPE_MAP = {
    "apt": "아파트",
    "apartment": "아파트",
    "아파트": "아파트",
    "officetel": "오피스텔",
    "오피스텔": "오피스텔",
    "villa": "연립다세대",
    "빌라": "연립다세대",
    "연립": "연립다세대",
    "다세대": "연립다세대",
    "다가구": "다가구",
    "단독": "단독주택",
    "단독주택": "단독주택",
}


@dataclass(frozen=True)
class NormalizedContract:
    address: str
    legal_dong_code: str
    housing_type: str
    deposit_won: int
    monthly_rent_won: int
    exclusive_area_m2: float
    floor: int | None
    built_year: int | None
    contract_stage: str
    missing_fields: list[str]


def normalize_housing_type(value: str) -> str:
    key = value.strip().lower()
    return HOUSING_TYPE_MAP.get(key, value.strip())


def normalize_contract(payload: ContractInput) -> NormalizedContract:
    missing = []
    for field in ["address", "legal_dong_code", "housing_type"]:
        if not getattr(payload, field):
            missing.append(field)
    if payload.deposit_won <= 0:
        missing.append("deposit_won")
    if payload.exclusive_area_m2 <= 0:
        missing.append("exclusive_area_m2")

    return NormalizedContract(
        address=payload.address.strip(),
        legal_dong_code=payload.legal_dong_code.strip(),
        housing_type=normalize_housing_type(payload.housing_type),
        deposit_won=int(payload.deposit_won),
        monthly_rent_won=int(payload.monthly_rent_won or 0),
        exclusive_area_m2=float(payload.exclusive_area_m2),
        floor=payload.floor,
        built_year=payload.built_year,
        contract_stage=payload.contract_stage.strip() or "계약 전 확인",
        missing_fields=missing,
    )
