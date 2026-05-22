from __future__ import annotations

from typing import Any


UNKNOWN = "모름"
YES = "있음"
NO = "없음"
CHECKED = "확인함"
UNCHECKED = "확인 못함"

YES_NO_UNKNOWN_KEYS = {
    "mortgage_flag",
    "seizure_flag",
    "provisional_seizure_flag",
    "trust_flag",
    "leasehold_registration_flag",
    "jeonse_right_flag",
    "ownership_transfer_recent_flag",
    "registry_warning_flag",
    "violation_flag",
    "non_residential_usage_flag",
    "rights_explained",
    "broker_signed",
}

CHECKED_STATE_KEYS = {
    "registry_checked",
    "building_register_checked",
    "broker_explanation_checked",
    "senior_deposit_checked",
}

NUMBER_DEFAULT_KEYS = {"mortgage_amount"}


def _bool_to_yes_no_unknown(value: Any) -> str:
    if value is True:
        return YES
    if value is False:
        return NO
    return UNKNOWN


def _bool_to_checked_state(value: Any) -> str:
    if value is True:
        return CHECKED
    if value is False:
        return UNCHECKED
    return UNKNOWN


def _has_review_default(value: Any) -> bool:
    return value is not None and value != ""


def apply_document_review_defaults(st: Any, defaults: dict[str, Any], *, overwrite: bool = True) -> list[str]:
    """Seed OCR-derived values into the review/correction widgets.

    Streamlit radio widgets store the displayed label in session_state. This
    function converts boolean OCR/parser candidates to those labels before the
    widgets are created, so users can review auto-filled values and edit only
    the wrong ones.
    """

    changed: list[str] = []
    for key, value in defaults.items():
        if not _has_review_default(value):
            continue
        if key in YES_NO_UNKNOWN_KEYS:
            widget_value = _bool_to_yes_no_unknown(value)
        elif key in CHECKED_STATE_KEYS:
            widget_value = _bool_to_checked_state(value)
        elif key in NUMBER_DEFAULT_KEYS:
            try:
                widget_value = int(float(value))
            except (TypeError, ValueError):
                continue
        else:
            continue

        current = st.session_state.get(key)
        if overwrite or key not in st.session_state:
            if current != widget_value:
                st.session_state[key] = widget_value
                changed.append(key)
    return changed


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
    st.caption("OCR 추출값을 먼저 자동 반영합니다. 값이 다르면 여기서 수정한 뒤 진단을 시작하세요.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**등기부등본 보완 입력**")
        registry_checked = _checked_state(st, "등기부등본을 확인했나요?", "registry_checked")
        mortgage_flag = _yes_no_unknown(st, "근저당권이 있나요?", "mortgage_flag")
        mortgage_amount = st.number_input("채권최고액", min_value=0, value=0, step=10_000_000, key="mortgage_amount")
        seizure_flag = _yes_no_unknown(st, "압류가 있나요?", "seizure_flag")
        provisional_seizure_flag = _yes_no_unknown(st, "가압류가 있나요?", "provisional_seizure_flag")
        trust_flag = _yes_no_unknown(st, "신탁등기가 있나요?", "trust_flag")
        jeonse_right_flag = _yes_no_unknown(st, "전세권 설정이 있나요?", "jeonse_right_flag")
        leasehold_registration_flag = _yes_no_unknown(st, "임차권등기가 있나요?", "leasehold_registration_flag")
        ownership_transfer_recent_flag = _yes_no_unknown(
            st,
            "소유권 이전·보존 등 소유권 변동 단서가 있나요?",
            "ownership_transfer_recent_flag",
        )
        registry_warning_flag = _yes_no_unknown(
            st,
            "가등기·경매·가처분 등 주의 권리관계가 있나요?",
            "registry_warning_flag",
        )

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
        "provisional_seizure_flag": provisional_seizure_flag,
        "trust_flag": trust_flag,
        "jeonse_right_flag": jeonse_right_flag,
        "leasehold_registration_flag": leasehold_registration_flag,
        "ownership_transfer_recent_flag": ownership_transfer_recent_flag,
        "registry_warning_flag": registry_warning_flag,
        "building_register_checked": building_register_checked,
        "violation_flag": violation_flag,
        "non_residential_usage_flag": non_residential_usage_flag,
        "broker_explanation_checked": broker_explanation_checked,
        "rights_explained": rights_explained,
        "broker_signed": broker_signed,
        "senior_deposit_checked": senior_deposit_checked,
    }
