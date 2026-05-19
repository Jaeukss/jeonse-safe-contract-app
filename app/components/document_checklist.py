from __future__ import annotations

from typing import Any


def render_document_checklist(st: Any) -> dict[str, Any]:
    st.subheader("3. 체크박스 보완")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**등기부등본 확인**")
        registry_checked = st.checkbox("등기부등본을 확인했습니다.")
        mortgage_flag = st.checkbox("근저당권이 있습니다.")
        seizure_flag = st.checkbox("압류 또는 가압류가 있습니다.")
        trust_flag = st.checkbox("신탁등기가 있습니다.")
        leasehold_registration_flag = st.checkbox("임차권등기가 있습니다.")
        registry_unknown = st.checkbox("등기부 권리관계를 잘 모르겠습니다.")
    with col2:
        st.markdown("**건축물대장/확인설명서**")
        building_register_checked = st.checkbox("건축물대장을 확인했습니다.")
        violation_flag = st.checkbox("위반건축물로 표시되어 있습니다.")
        non_residential_usage_flag = st.checkbox("주용도가 주택이 아닙니다.")
        broker_explanation_checked = st.checkbox("중개대상물 확인설명서를 받았습니다.")
        rights_explained = st.checkbox("권리관계 설명을 들었습니다.")
        broker_signed = st.checkbox("공인중개사 서명 또는 날인이 있습니다.")
        senior_deposit_checked = st.checkbox("다가구 선순위 임차보증금을 확인했습니다.")
    data = {
        "registry_checked": registry_checked,
        "mortgage_flag": None if registry_unknown else mortgage_flag,
        "seizure_flag": None if registry_unknown else seizure_flag,
        "provisional_seizure_flag": None if registry_unknown else seizure_flag,
        "trust_flag": None if registry_unknown else trust_flag,
        "leasehold_registration_flag": None if registry_unknown else leasehold_registration_flag,
        "building_register_checked": building_register_checked,
        "violation_flag": violation_flag if building_register_checked else None,
        "non_residential_usage_flag": non_residential_usage_flag if building_register_checked else None,
        "broker_explanation_checked": broker_explanation_checked,
        "rights_explained": rights_explained if broker_explanation_checked else None,
        "broker_signed": broker_signed if broker_explanation_checked else None,
        "senior_deposit_checked": senior_deposit_checked,
    }
    return data
