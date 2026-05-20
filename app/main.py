from __future__ import annotations

import json
import re
from uuid import uuid4

import pandas as pd
import streamlit as st

from app.components.basic_input import render_basic_input
from app.components.conflict_view import render_conflict_view
from app.components.document_review import render_document_review
from app.components.document_upload import render_document_upload
from app.components.report_view import render_report_view
from src.agent.graph import run_agent_workflow
from src.input_layer.raw_store import save_raw_input


TARGET_DISTRICTS = ("관악구", "강서구")


def _normalize_address(value: object) -> str:
    text = str(value or "")
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def _has_specific_address(value: str) -> bool:
    return bool(re.search(r"\d", value))


def _to_bool(value: object) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "y", "yes", "위반"}:
        return True
    if text in {"false", "0", "n", "no", ""}:
        return False
    return None


def _match_score(user_address: str, row: pd.Series) -> int:
    normalized_user = _normalize_address(user_address)
    addresses = [
        _normalize_address(row.get("address_normalized")),
        _normalize_address(row.get("road_address")),
    ]
    if not normalized_user:
        return 0
    for address in addresses:
        if not address:
            continue
        if normalized_user in address or address in normalized_user:
            return 100

    tokens = [token for token in re.split(r"\s+", user_address.strip()) if len(token) >= 2]
    score = 0
    joined = " ".join(str(row.get(column, "")) for column in ["address_normalized", "road_address"])
    for token in tokens:
        if token in joined:
            score += 10
    return score


def match_public_building(address: str) -> dict[str, object] | None:
    if not _has_specific_address(address):
        return None
    path = "data/processed/ganak_building_clean.csv"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return None
    if df.empty:
        return None

    df = df.copy()
    df["_match_score"] = df.apply(lambda row: _match_score(address, row), axis=1)
    candidates = df[df["_match_score"].ge(30)].sort_values("_match_score", ascending=False)
    if candidates.empty:
        return None

    row = candidates.iloc[0]
    main_usage = "" if pd.isna(row.get("main_usage")) else str(row.get("main_usage"))
    return {
        "public_building_matched": True,
        "public_building_gross_area_m2": float(row["area_m2"]) if pd.notna(row.get("area_m2")) else None,
        "approval_year": int(row["approval_year"]) if pd.notna(row.get("approval_year")) else None,
        "violation_flag": _to_bool(row.get("violation_flag")),
        "main_usage": main_usage or None,
        "non_residential_usage_flag": ("주택" not in main_usage) if main_usage else None,
    }


def run_diagnosis(session_id: str, records: list[dict[str, object]], resolutions: dict[str, object] | None = None) -> dict[str, object]:
    result = run_agent_workflow({"session_id": session_id, "records": records, "resolutions": resolutions or {}})
    return dict(result)


def main() -> None:
    st.set_page_config(page_title="전세계약 위험진단 MVP", page_icon="H", layout="wide")
    st.title("전세계약 위험진단 MVP")
    st.caption("OCR 텍스트 추출 후 실패·불확실 항목은 사용자 수기 입력과 선택지 입력으로 보완합니다.")

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"S-{uuid4().hex[:8].upper()}"
    session_id = st.session_state.session_id

    with st.form("diagnosis_form"):
        basic = render_basic_input(st)
        manual_correction = render_document_review(st)
        submitted = st.form_submit_button("입력 저장", type="primary", use_container_width=True)

    upload_records = render_document_upload(st, session_id)

    if submitted:
        if not any(district in basic["address"] for district in TARGET_DISTRICTS):
            st.error("이번 MVP는 관악구 또는 강서구 주소만 지원합니다.")
            return
        records: list[dict[str, object]] = []
        records.append(save_raw_input(session_id, "user_input", basic))
        records.append(save_raw_input(session_id, "manual_correction", manual_correction))
        public_building = match_public_building(basic["address"])
        if public_building:
            records.append(save_raw_input(session_id, "public_building_data", public_building))
        records.extend(upload_records)
        result = run_diagnosis(session_id, records)
        st.session_state.pending_records = records
        st.session_state.pending_conflicts = result.get("conflicts", [])
        st.session_state.last_result = result

    if st.session_state.get("pending_conflicts"):
        resolutions = render_conflict_view(st, st.session_state.pending_conflicts)
        if st.button("선택값으로 재진단", type="primary"):
            st.session_state.last_result = run_diagnosis(session_id, st.session_state.pending_records, resolutions)
            st.session_state.pending_conflicts = []

    if st.session_state.get("last_result"):
        render_report_view(st, st.session_state.last_result)
        with st.expander("진단 JSON"):
            st.code(json.dumps(st.session_state.last_result, ensure_ascii=False, indent=2), language="json")


if __name__ == "__main__":
    main()
