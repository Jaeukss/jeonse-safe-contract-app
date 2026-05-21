from __future__ import annotations

import re
from typing import Any


HOUSING_TYPES = ["아파트", "오피스텔", "연립다세대", "다가구"]
CONTRACT_STAGES = ["매물 검토", "계약 전 확인", "계약 당일", "잔금 전", "입주 직전"]

BASIC_FIELD_KEYS = {
    "address": "basic_address",
    "housing_type": "basic_housing_type",
    "contract_stage": "basic_contract_stage",
    "deposit": "basic_deposit",
    "monthly_rent": "basic_monthly_rent",
    "area_m2": "basic_area_m2",
    "floor": "basic_floor",
    "built_year": "basic_built_year",
}

DEFAULT_BASIC_VALUES = {
    "address": "서울시 관악구 신림동",
    "housing_type": "다가구",
    "contract_stage": "계약 전 확인",
    "deposit": 250_000_000,
    "monthly_rent": 0,
    "area_m2": 45.0,
    "floor": 3,
    "built_year": 2005,
}


def _coerce_value(field: str, value: Any) -> Any:
    if field in {"deposit", "monthly_rent", "floor", "built_year"}:
        coerced = int(float(value))
        if field == "floor" and not -5 <= coerced <= 80:
            raise ValueError("floor out of range")
        return coerced
    if field == "area_m2":
        coerced = float(value)
        if coerced <= 0 or coerced > 500:
            raise ValueError("area_m2 out of range")
        return coerced
    if field == "housing_type" and value not in HOUSING_TYPES:
        return DEFAULT_BASIC_VALUES[field]
    if field == "contract_stage" and value not in CONTRACT_STAGES:
        return DEFAULT_BASIC_VALUES[field]
    return value


def apply_basic_defaults(st: Any, defaults: dict[str, Any], *, overwrite: bool = False, overwrite_defaults: bool = False) -> list[str]:
    changed: list[str] = []
    for field, key in BASIC_FIELD_KEYS.items():
        if field not in defaults or defaults[field] in (None, ""):
            continue
        try:
            value = _coerce_value(field, defaults[field])
        except (TypeError, ValueError):
            continue
        current = st.session_state.get(key)
        should_apply = key not in st.session_state or overwrite
        if overwrite_defaults and current == DEFAULT_BASIC_VALUES.get(field):
            should_apply = True
        if should_apply and current != value:
            st.session_state[key] = value
            changed.append(field)
    return changed


def _district_from_address(address: str) -> str:
    if "관악구" in address:
        return "관악구"
    if "강서구" in address:
        return "강서구"
    return ""


def _dong_from_address(address: str) -> str:
    match = re.search(r"([가-힣0-9]+동)", address)
    return match.group(1) if match else ""


def render_basic_input(st: Any, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    initial = {**DEFAULT_BASIC_VALUES, **defaults}
    apply_basic_defaults(st, initial)
    st.subheader("1. 기본 정보 입력")
    col1, col2 = st.columns(2)
    with col1:
        address = st.text_input("주소", key="basic_address")
        housing_type = st.selectbox(
            "주택유형",
            HOUSING_TYPES,
            key="basic_housing_type",
        )
        contract_stage = st.selectbox("계약 단계", CONTRACT_STAGES, key="basic_contract_stage")
    with col2:
        deposit = st.number_input("보증금", min_value=0, step=10_000_000, key="basic_deposit")
        monthly_rent = st.number_input("월세", min_value=0, step=50_000, key="basic_monthly_rent")
        area_m2 = st.number_input("전용면적(㎡)", min_value=1.0, step=1.0, key="basic_area_m2")
        floor = st.number_input("층", min_value=-5, max_value=80, step=1, key="basic_floor")
        built_year = st.number_input("건축연도", min_value=1900, max_value=2100, step=1, key="basic_built_year")

    return {
        "address": address,
        "district": _district_from_address(address),
        "dong": _dong_from_address(address),
        "housing_type": housing_type,
        "deposit": int(deposit),
        "monthly_rent": int(monthly_rent),
        "area_m2": float(area_m2),
        "floor": int(floor),
        "built_year": int(built_year),
        "contract_stage": contract_stage,
    }
