from __future__ import annotations

from typing import Any


UNKNOWN = "모름"
YES = "있음"
NO = "없음"
CHECKED = "확인함"
UNCHECKED = "확인 못함"


def _yes_no_unknown(st: Any, label: str, key: str) -> bool | None:
    value = st.radio(label, [UNKNOWN, YES, NO], key=key, horizontal=True)
    if value == UNKNOWN:
        return None
    return value == YES


def _checked_state(st: Any, label: str, key: str) -> bool | None:
    value = st.radio(label, [UNKNOWN, CHECKED, UNCHECKED], key=key, horizontal=True)
    if value == UNKNOWN:
        return None
    return value == CHECKED


def render_document_review(st: Any) -> dict[str, Any]:
    st.subheader("3. OCR 결과 확인 및 보완 입력")
    st.caption("OCR 추출 실패 또는 불확실 항목은 직접 입력하거나 선택지로 보완합니다.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**등기부등본 보완 입력**")
        registry_checked = _checked_state(st, "등기부등본을 확인했나요?", "registry_checked")
        mortgage_flag = _yes_no_unknown(st, "근저당권이 있나요?", "mortgage_flag")
        mortgage_amount = st.number_input("채권최고액", min_value=0, value=0, step=10_000_000)
        seizure_flag = _yes_no_unknown(st, "압류 또는 가압류가 있나요?", "seizure_flag")
        trust_flag = _yes_no_unknown(st, "신탁등기가 있나요?", "trust_flag")
        leasehold_registration_flag = _yes_no_unknown(st, "임차권등기가 있나요?", "leasehold_registration_flag")

    with col2:
        st.markdown("**건축물대장·확인설명서 보완 입력**")
        building_register_checked = _checked_state(st, "건축물대장을 확인했나요?", "building_register_checked")
        violation_flag = _yes_no_unknown(st, "위반건축물로 표시되어 있나요?", "violation_flag")
        non_residential_usage_flag = _yes_no_unknown(st, "주용도가 주택이 아닌가요?", "non_residential_usage_flag")
        broker_explanation_checked = _checked_state(st, "중개대상물 확인설명서를 받았나요?", "broker_explanation_checked")
        rights_explained = _yes_no_unknown(st, "권리관계 설명을 들었나요?", "rights_explained")
        broker_signed = _yes_no_unknown(st, "공인중개사 서명 또는 날인이 있나요?", "broker_signed")
        senior_deposit_checked = _checked_state(st, "다가구 선순위 임차보증금을 확인했나요?", "senior_deposit_checked")

    return {
        "registry_checked": registry_checked,
        "mortgage_flag": mortgage_flag,
        "mortgage_amount": int(mortgage_amount) if mortgage_amount else None,
        "seizure_flag": seizure_flag,
        "provisional_seizure_flag": seizure_flag,
        "trust_flag": trust_flag,
        "leasehold_registration_flag": leasehold_registration_flag,
        "building_register_checked": building_register_checked,
        "violation_flag": violation_flag,
        "non_residential_usage_flag": non_residential_usage_flag,
        "broker_explanation_checked": broker_explanation_checked,
        "rights_explained": rights_explained,
        "broker_signed": broker_signed,
        "senior_deposit_checked": senior_deposit_checked,
    }
