from __future__ import annotations

import re
from typing import Any


HOUSING_TYPES = ["아파트", "오피스텔", "연립다세대", "다가구"]
CONTRACT_STAGES = ["매물 검토", "계약 전 확인", "계약 당일", "잔금 전", "입주 직전"]


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
    st.subheader("1. 기본 정보 입력")
    col1, col2 = st.columns(2)
    with col1:
        address = st.text_input("주소", defaults.get("address", "서울시 관악구 신림동"))
        default_housing_type = defaults.get("housing_type", "다가구")
        housing_type = st.selectbox(
            "주택유형",
            HOUSING_TYPES,
            index=HOUSING_TYPES.index(default_housing_type) if default_housing_type in HOUSING_TYPES else 3,
        )
        contract_stage = st.selectbox("계약 단계", CONTRACT_STAGES, index=1)
    with col2:
        deposit = st.number_input("보증금", min_value=0, value=int(defaults.get("deposit", 250_000_000)), step=10_000_000)
        monthly_rent = st.number_input("월세", min_value=0, value=int(defaults.get("monthly_rent", 0)), step=50_000)
        area_m2 = st.number_input("전용면적(㎡)", min_value=1.0, value=float(defaults.get("area_m2", 45.0)), step=1.0)
        floor = st.number_input("층", min_value=-5, max_value=80, value=int(defaults.get("floor", 3)), step=1)

    return {
        "address": address,
        "district": _district_from_address(address),
        "dong": _dong_from_address(address),
        "housing_type": housing_type,
        "deposit": int(deposit),
        "monthly_rent": int(monthly_rent),
        "area_m2": float(area_m2),
        "floor": int(floor),
        "contract_stage": contract_stage,
    }
