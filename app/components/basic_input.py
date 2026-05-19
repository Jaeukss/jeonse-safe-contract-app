from __future__ import annotations

from typing import Any


def render_basic_input(st: Any, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    st.subheader("1. 기본 정보 입력")
    col1, col2 = st.columns(2)
    with col1:
        address = st.text_input("주소", defaults.get("address", "서울시 관악구 신림동"))
        housing_type = st.selectbox(
            "주택유형",
            ["아파트", "오피스텔", "연립다세대", "다가구"],
            index=["아파트", "오피스텔", "연립다세대", "다가구"].index(defaults.get("housing_type", "다가구"))
            if defaults.get("housing_type", "다가구") in ["아파트", "오피스텔", "연립다세대", "다가구"]
            else 3,
        )
        contract_stage = st.selectbox("계약 단계", ["매물 검토", "계약 전 확인", "계약 당일", "잔금 전"], index=1)
    with col2:
        deposit = st.number_input("보증금", min_value=0, value=int(defaults.get("deposit", 250_000_000)), step=10_000_000)
        monthly_rent = st.number_input("월세", min_value=0, value=int(defaults.get("monthly_rent", 0)), step=50_000)
        area_m2 = st.number_input("전용면적(㎡)", min_value=1.0, value=float(defaults.get("area_m2", 45.0)), step=1.0)
        floor = st.number_input("층", min_value=-5, max_value=80, value=int(defaults.get("floor", 3)), step=1)
    dong = "신림동" if "신림" in address else ""
    return {
        "address": address,
        "district": "관악구" if "관악" in address else "",
        "dong": dong,
        "housing_type": housing_type,
        "deposit": int(deposit),
        "monthly_rent": int(monthly_rent),
        "area_m2": float(area_m2),
        "floor": int(floor),
        "contract_stage": contract_stage,
    }
