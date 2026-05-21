from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st

from app.components.basic_input import apply_basic_defaults, render_basic_input
from app.components.conflict_view import render_conflict_view
from app.components.document_review import render_document_review
from app.components.document_upload import render_document_upload
from app.components.report_view import render_report_view
from src.agent.graph import run_agent_workflow
from src.data_bootstrap import ensure_data_available
from src.input_layer.raw_store import save_raw_input


ROOT = Path(__file__).resolve().parents[1]
BUILDING_DATA_PATHS = [
    ROOT / "data" / "processed" / "gwanak_gangseo_building_title_clean.csv",
    ROOT / "data" / "processed" / "ganak_building_clean.csv",
]
TARGET_DISTRICTS = ("관악구", "강서구")


def _money(value: int | float | None) -> str:
    if not value:
        return "-"
    value = int(value)
    if value >= 100_000_000:
        eok = value // 100_000_000
        man = (value % 100_000_000) // 10_000
        return f"{eok}억 {man:,}만원" if man else f"{eok}억원"
    return f"{value // 10_000:,}만원"


def _normalize_address(address: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", str(address or "")).lower()


def _strip_address_suffix(address: str) -> str:
    compact = re.sub(r"[^0-9A-Za-z가-힣-]", "", str(address or "")).lower()
    return compact.replace("번지", "")


def _has_specific_address(address: str) -> bool:
    return bool(re.search(r"\d", str(address or "")))


def _extract_lot_parts(address: str) -> tuple[str, int, int] | None:
    match = re.search(r"([가-힣0-9]+동)\s*(\d+)(?:-(\d+))?", str(address or ""))
    if not match:
        return None
    return match.group(1), int(match.group(2)), int(match.group(3) or 0)


def _row_lot_parts(row: pd.Series) -> tuple[str, int, int] | None:
    lot_address = str(row.get("lot_address") or row.get("address_normalized") or "")
    dong_match = re.search(r"([가-힣0-9]+동)", lot_address)
    if not dong_match:
        return None
    try:
        bun = int(str(row.get("bun", "")).strip() or "0")
        ji = int(str(row.get("ji", "")).strip() or "0")
    except ValueError:
        lot_match = re.search(r"(\d+)(?:-(\d+))?번지", lot_address)
        if not lot_match:
            return None
        bun = int(lot_match.group(1))
        ji = int(lot_match.group(2) or 0)
    return dong_match.group(1), bun, ji


def _to_bool(value: Any) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "y", "yes", "위반", "해당"}:
        return True
    if text in {"false", "0", "n", "no", "정상", "미해당"}:
        return False
    return None


def _match_score(query: str, row: pd.Series) -> int:
    query_norm = _strip_address_suffix(query)
    query_lot = _extract_lot_parts(query)
    row_lot = _row_lot_parts(row)
    if query_lot and row_lot and query_lot == row_lot:
        return 95
    if query_lot:
        return 0

    lot_address = row.get("address_normalized")
    if not isinstance(lot_address, str) or not lot_address.strip():
        lot_address = row.get("lot_address", "")
    candidates = [
        _strip_address_suffix(lot_address),
        _strip_address_suffix(row.get("road_address", "")),
    ]
    score = 0
    for candidate in candidates:
        if not candidate:
            continue
        if query_norm == candidate:
            score = max(score, 100)
        elif not any(ch.isdigit() for ch in query_norm) and (query_norm in candidate or candidate in query_norm):
            score = max(score, 80)
    return score


@st.cache_data(show_spinner=False)
def _load_building_data() -> pd.DataFrame:
    for path in BUILDING_DATA_PATHS:
        if path.exists():
            return pd.read_csv(path, low_memory=False)
    return pd.DataFrame()


def match_public_building(address: str) -> dict[str, Any] | None:
    if not _has_specific_address(address):
        return None
    df = _load_building_data()
    if df.empty:
        return None

    scored = df.copy()
    scored["_score"] = scored.apply(lambda row: _match_score(address, row), axis=1)
    best = scored.sort_values("_score", ascending=False).head(1)
    if best.empty or int(best.iloc[0]["_score"]) < 80:
        return None

    row = best.iloc[0]
    main_usage = row.get("main_usage")
    lot_address = row.get("address_normalized")
    if not isinstance(lot_address, str) or not lot_address.strip():
        lot_address = row.get("lot_address")
    gross_area = row.get("gross_area_m2")
    if pd.isna(gross_area):
        gross_area = row.get("area_m2")
    public_data = {
        "public_building_matched": True,
        "public_building_match_score": int(row["_score"]),
        "building_register_pk": str(row.get("building_register_pk")) if pd.notna(row.get("building_register_pk")) else None,
        "legal_dong_code": str(row.get("legal_dong_code")) if pd.notna(row.get("legal_dong_code")) else None,
        "bun": str(row.get("bun")) if pd.notna(row.get("bun")) else None,
        "ji": str(row.get("ji")) if pd.notna(row.get("ji")) else None,
        "public_building_address": lot_address,
        "public_building_road_address": row.get("road_address"),
        "public_building_gross_area_m2": float(gross_area) if pd.notna(gross_area) else None,
        "approval_year": int(row["approval_year"]) if pd.notna(row.get("approval_year")) else None,
        "violation_flag": _to_bool(row.get("violation_flag")),
    }
    if isinstance(main_usage, str) and main_usage.strip():
        public_data["main_usage"] = main_usage
        public_data["non_residential_usage_flag"] = not any(keyword in main_usage for keyword in ("주택", "아파트", "다가구"))
    return public_data


def run_diagnosis(session_id: str, records: list[dict[str, Any]], resolutions: dict[str, Any] | None = None) -> dict[str, Any]:
    return run_agent_workflow({"session_id": session_id, "records": records, "resolutions": resolutions or {}})


def _simple_simulation_score(deposit: int, sale_price: int, mortgage_amount: int) -> tuple[int, float, str]:
    if not sale_price:
        return 0, 0.0, "검토불가"
    ratio = round(deposit / sale_price * 100, 1)
    score = 0
    if ratio >= 90:
        score += 35
    elif ratio >= 80:
        score += 22
    elif ratio >= 70:
        score += 10
    if mortgage_amount and (deposit + mortgage_amount) / sale_price >= 0.9:
        score += 35
    elif mortgage_amount and (deposit + mortgage_amount) / sale_price >= 0.8:
        score += 20

    if score >= 75:
        grade = "고위험"
    elif score >= 50:
        grade = "위험"
    elif score >= 25:
        grade = "주의"
    else:
        grade = "확인 양호"
    return score, ratio, grade


def render_positioning_intro() -> str:
    st.title("전세계약 안심진단")
    st.caption("계약 전에 보증금, 시세, 등기부·건축물대장, 문서 확인 상태를 한 번에 점검하는 임차인용 MVP입니다.")
    st.info(
        "이 서비스는 법률 판단을 대신하지 않습니다. 위험 신호가 나오면 계약을 서두르지 말고 공인중개사, HUG, 지자체 상담창구 또는 법률 전문가에게 확인하세요."
    )

    with st.expander("처음 사용하는 분을 위한 진행 순서", expanded=True):
        cols = st.columns(3)
        cols[0].markdown("**1. 문서 준비**\n\n등기부등본, 건축물대장, 계약서 내용을 업로드하거나 붙여넣습니다.")
        cols[1].markdown("**2. 계약 정보 입력**\n\n주소, 보증금, 면적, 층, 건축연도 등 알고 있는 값을 입력합니다.")
        cols[2].markdown("**3. 결과 확인**\n\n위험등급, 이유, 다음 행동, 공식 근거 링크를 확인합니다.")

    st.markdown("### 서비스 포지셔닝")
    st.markdown(
        "HUG/KB가 결과형 전세안전진단에 가깝다면, 이 MVP는 **OCR 오류·서류 누락·입력 충돌까지 감안해 사용자가 계약 전 확인해야 할 정보를 끝까지 정리하는 증거 기반 전세계약 위험진단 AI Agent**입니다."
    )
    user_mode = st.segmented_control(
        "사용자 모드",
        ["일반 임차인", "공인중개사/컨설턴트"],
        default="일반 임차인",
        help="일반 임차인은 쉬운 설명 중심, 전문가 모드는 근거와 스냅샷 중심으로 리포트 해석 방향을 잡습니다.",
    )
    return str(user_mode or "일반 임차인")


def render_document_prep_cards() -> None:
    st.markdown("### 업로드하면 좋은 파일")
    st.caption("모든 파일이 없어도 진단은 가능하지만, 문서가 많을수록 결과 신뢰도가 올라갑니다.")
    docs = [
        {
            "title": "등기부등본 또는 등기사항전부증명서",
            "body": "소유자, 근저당권, 압류, 가압류, 신탁등기 등 권리관계를 확인합니다.",
            "where": "대법원 인터넷등기소",
            "how": "계약 직전 최신본을 발급하고 근저당권·채권최고액·말소 조건을 확인합니다.",
            "url": "https://www.iros.go.kr",
        },
        {
            "title": "건축물대장",
            "body": "주용도, 면적, 층, 사용승인일, 위반건축물 표시 여부를 확인합니다.",
            "where": "정부24 또는 세움터",
            "how": "주소와 호실이 계약서와 맞는지 대조합니다.",
            "url": "https://www.gov.kr",
        },
        {
            "title": "임대차계약서 초안 또는 표준계약서",
            "body": "보증금, 잔금일, 특약, 근저당 말소 조건, 확정일자 관련 내용을 확인합니다.",
            "where": "법무부 자료실",
            "how": "표준계약서 항목과 비교해 빠진 특약이 없는지 봅니다.",
            "url": "https://www.moj.go.kr",
        },
        {
            "title": "중개대상물 확인설명서",
            "body": "중개사가 설명한 권리관계, 시설 상태, 거래 조건이 실제 문서와 맞는지 확인합니다.",
            "where": "공인중개사에게 요청",
            "how": "등기부등본·건축물대장과 서로 맞는지 대조합니다.",
            "url": "https://www.law.go.kr",
        },
        {
            "title": "HUG 전세보증금반환보증 신청 준비서류",
            "body": "보증 가입 가능성, 보증한도, 제출서류를 확인합니다.",
            "where": "모바일 HUG",
            "how": "보증금이 높은 경우 계약 전 보증 가능성을 먼저 확인합니다.",
            "url": "https://www.khug.or.kr",
        },
    ]

    for row_start in range(0, len(docs), 2):
        cols = st.columns(2)
        for col, item in zip(cols, docs[row_start : row_start + 2]):
            with col.container(border=True):
                st.markdown(f"**{item['title']}**")
                st.write(item["body"])
                st.markdown(f"**어디서:** {item['where']}")
                st.markdown(f"**방법:** {item['how']}")
                st.link_button("공식 사이트 열기", item["url"], use_container_width=True)


def render_action_checklist(user_mode: str) -> None:
    st.markdown("### 계약 전 행동 체크")
    if user_mode == "일반 임차인":
        st.checkbox("인터넷등기소에서 등기부등본 최신본을 발급하고 근저당권·압류·신탁 여부를 확인했습니다.")
        st.checkbox("정부24 또는 세움터에서 건축물대장을 확인하고 주소·호실·용도·위반건축물 여부를 대조했습니다.")
        st.checkbox("중개사에게 근저당 말소 조건, 선순위 임차보증금, 신탁 여부를 질문했습니다.")
        st.checkbox("HUG 전세보증금반환보증 가능성과 예상 보증한도를 확인했습니다.")
    else:
        st.checkbox("등기부등본 발급일, 갑구·을구 권리관계, 채권최고액을 스냅샷 근거로 남겼습니다.")
        st.checkbox("건축물대장 PK, 주용도, 전유/연면적, 위반건축물 여부를 입력값과 대조했습니다.")
        st.checkbox("보증금, 선순위 권리, 예상 매매가 기준 전세가율 검토표를 작성했습니다.")
        st.checkbox("임차인에게 추가 확인 필요 항목과 공식 확인 링크를 리포트로 전달할 준비가 됐습니다.")

    with st.expander("중개사에게 바로 물어볼 질문"):
        st.markdown(
            "- 이 집의 근저당권 채권최고액은 얼마이고, 잔금 전에 말소되는 조건인가요?\n"
            "- 다가구라면 선순위 임차보증금 총액을 확인할 수 있나요?\n"
            "- 신탁등기가 있다면 임대 권한과 수탁자 동의는 어떻게 확인하나요?\n"
            "- 등기부등본과 건축물대장 내용이 계약서 주소·호실과 모두 일치하나요?\n"
            "- HUG 전세보증금반환보증 가입에 제한되는 조건이 있나요?"
        )


def render_risk_simulator() -> None:
    st.markdown("### 보증금 조정 시뮬레이터")
    st.caption("간이 계산입니다. 실제 진단은 아래 입력값, OCR 결과, 사용자 보완값, 유사 거래 기반 가격 예측을 함께 반영합니다.")
    col1, col2, col3 = st.columns(3)
    with col1:
        current_deposit = st.number_input("현재 보증금", min_value=0, value=250_000_000, step=10_000_000)
    with col2:
        adjusted_deposit = st.number_input("조정 후 보증금", min_value=0, value=230_000_000, step=10_000_000)
    with col3:
        estimated_sale_price = st.number_input("추정 매매가", min_value=0, value=320_000_000, step=10_000_000)
    mortgage_amount = st.number_input("채권최고액이 있으면 입력", min_value=0, value=0, step=10_000_000)

    before_score, before_ratio, before_grade = _simple_simulation_score(current_deposit, estimated_sale_price, mortgage_amount)
    after_score, after_ratio, after_grade = _simple_simulation_score(adjusted_deposit, estimated_sale_price, mortgage_amount)
    cols = st.columns(4)
    cols[0].metric("현재 전세가율", f"{before_ratio}%", before_grade)
    cols[1].metric("조정 후 전세가율", f"{after_ratio}%", after_grade)
    cols[2].metric("간이 위험점수 변화", f"{before_score}점", f"{after_score - before_score:+}점")
    cols[3].metric("보증금 조정폭", _money(current_deposit - adjusted_deposit))


def render_pre_input_section() -> str:
    user_mode = render_positioning_intro()
    render_document_prep_cards()
    render_action_checklist(user_mode)
    render_risk_simulator()
    st.divider()
    st.markdown("## 진단 데이터 입력")
    st.caption("여기부터 입력한 값은 출처별 Raw Data로 저장되고, OCR 결과와 사용자 보완값이 충돌하면 사용자가 최종 확정합니다.")
    return user_mode


def main() -> None:
    st.set_page_config(page_title="전세계약 안심진단", page_icon="H", layout="wide")
    data_status = ensure_data_available()
    with st.sidebar:
        st.markdown("### 데이터 상태")
        if data_status.ready:
            st.success(data_status.message)
        else:
            st.error(data_status.message)
        if data_status.enriched_missing:
            st.caption("보조 데이터 일부 없음: " + ", ".join(data_status.enriched_missing[:2]))
        if data_status.source:
            st.caption(f"데이터 소스: {data_status.source}")

    session_id = st.session_state.setdefault("session_id", f"S-{uuid4().hex[:8].upper()}")
    user_mode = render_pre_input_section()
    st.session_state["user_mode"] = user_mode

    quick_cases = {
        "직접 입력": None,
        "안전에 가까운 사례": {
            "address": "서울시 관악구 신림동",
            "housing_type": "다가구",
            "deposit": 90_000_000,
            "monthly_rent": 0,
            "area_m2": 27.1,
            "floor": 2,
            "built_year": 2004,
        },
        "전세가율이 높은 빌라": {
            "address": "서울 강서구 화곡동 1027-8 해든빌라 402호",
            "housing_type": "연립다세대",
            "deposit": 270_000_000,
            "monthly_rent": 0,
            "area_m2": 42.1,
            "floor": 4,
            "built_year": 2016,
        },
        "신탁 확인이 필요한 다가구": {
            "address": "서울시 관악구 봉천동 1-52",
            "housing_type": "다가구",
            "deposit": 650_000_000,
            "monthly_rent": 0,
            "area_m2": 60.0,
            "floor": 2,
            "built_year": 1991,
        },
    }
    selected_case = st.selectbox("빠른 테스트 예시", list(quick_cases.keys()), key="quick_case")
    defaults = quick_cases[selected_case] or {}
    if selected_case != st.session_state.get("last_applied_quick_case") and defaults:
        apply_basic_defaults(st, defaults, overwrite=True)
        st.session_state["last_applied_quick_case"] = selected_case

    upload_records = render_document_upload(st, session_id)

    with st.form("diagnosis_form"):
        basic_input = render_basic_input(st, defaults)
        manual_correction = render_document_review(st)
        submitted = st.form_submit_button("안심진단 시작", use_container_width=True)

    if submitted:
        if not any(district in basic_input["address"] for district in TARGET_DISTRICTS):
            st.error("현재 MVP는 관악구와 강서구 주소만 지원합니다.")
            return

        records: list[dict[str, Any]] = []
        records.append(save_raw_input(session_id, "user_input", basic_input))

        cleaned_manual = {key: value for key, value in manual_correction.items() if value is not None}
        if cleaned_manual:
            records.append(save_raw_input(session_id, "manual_correction", cleaned_manual))

        public_building = match_public_building(basic_input["address"])
        if public_building:
            records.append(save_raw_input(session_id, "public_building_data", public_building))

        records.extend(upload_records)
        first_result = run_diagnosis(session_id, records)
        st.session_state["records"] = records
        st.session_state["pending_result"] = first_result
        st.session_state["result"] = first_result

    pending = st.session_state.get("pending_result")
    if pending and pending.get("conflicts"):
        resolutions = render_conflict_view(st, pending["conflicts"])
        if st.button("확정값으로 다시 진단", use_container_width=True):
            st.session_state["result"] = run_diagnosis(session_id, st.session_state["records"], resolutions)
            st.session_state["pending_result"] = None

    result = st.session_state.get("result")
    if result:
        render_report_view(st, result)


if __name__ == "__main__":
    main()
