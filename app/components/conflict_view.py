from __future__ import annotations

import json
from typing import Any


SOURCE_LABELS = {
    "user_input": "기본 입력",
    "manual_correction": "사용자 보완 입력",
    "user_checklist": "사용자 보완 입력",
    "registry_ocr": "등기부등본 OCR",
    "building_ocr": "건축물대장 OCR",
    "explanation_ocr": "확인설명서 OCR",
    "public_building_data": "공공 건축물대장",
    "market_data": "실거래가 데이터",
    "user_resolution": "사용자 최종 선택",
}

CHECK_FIELDS = {
    "registry_checked",
    "building_register_checked",
    "broker_explanation_checked",
    "senior_deposit_checked",
}

FIELD_LABELS = {
    "area_m2": "전용면적",
    "building_register_checked": "건축물대장 확인 여부",
    "registry_checked": "등기부등본 확인 여부",
    "broker_explanation_checked": "중개대상물 확인설명서 수령 여부",
    "mortgage_flag": "근저당권 여부",
    "mortgage_amount": "채권최고액",
    "seizure_flag": "압류 여부",
    "provisional_seizure_flag": "가압류 여부",
    "trust_flag": "신탁등기 여부",
    "leasehold_registration_flag": "임차권등기 여부",
    "violation_flag": "위반건축물 여부",
    "non_residential_usage_flag": "주용도 비주택 여부",
}


def _source_label(source: str) -> str:
    return SOURCE_LABELS.get(source, source)


def _field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def _format_value(field: str, value: Any) -> str:
    if value is None or value == "unknown" or value == "":
        return "모름"
    if isinstance(value, bool):
        if field in CHECK_FIELDS:
            return "확인함" if value else "확인 못함"
        return "있음" if value else "없음"
    if field in {"area_m2"}:
        return f"{float(value):g}㎡"
    if field in {"deposit", "monthly_rent", "mortgage_amount"}:
        return f"{int(value):,}원"
    return str(value)


def _option_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _unique_options(conflict: dict[str, Any]) -> list[Any]:
    values = [
        conflict["recommended"].get("value"),
        conflict["left"].get("value"),
        conflict["right"].get("value"),
        None,
    ]
    seen: set[str] = set()
    options: list[Any] = []
    for value in values:
        key = _option_key(value)
        if key in seen:
            continue
        seen.add(key)
        options.append(value)
    return options


def render_conflict_view(st: Any, conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    if not conflicts:
        return {}
    st.subheader("4. 충돌 확인")
    st.warning("OCR 추출값, 사용자 보완 입력, 기본 입력, 공공데이터 사이에 다른 값이 발견되었습니다. 진단에 사용할 값을 선택하세요.")
    resolutions: dict[str, Any] = {}
    for conflict in conflicts:
        field = conflict["field"]
        left = conflict["left"]
        right = conflict["right"]
        st.markdown(f"**항목: {_field_label(field)}**")
        st.caption(
            f"{_source_label(left['source'])}: {_format_value(field, left['value'])} / "
            f"{_source_label(right['source'])}: {_format_value(field, right['value'])}"
        )
        options = _unique_options(conflict)
        labels = [_format_value(field, value) for value in options]
        choice = st.radio(
            "진단에 사용할 값",
            options=list(range(len(options))),
            format_func=lambda index, labels=labels: labels[index],
            key=f"resolve_{field}",
            horizontal=True,
        )
        resolutions[field] = options[choice]
    return resolutions
