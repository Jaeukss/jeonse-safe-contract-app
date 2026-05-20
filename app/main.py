from __future__ import annotations

import json
from uuid import uuid4

import pandas as pd
import streamlit as st

from app.components.basic_input import render_basic_input
from app.components.conflict_view import render_conflict_view
from app.components.document_checklist import render_document_checklist
from app.components.document_upload import render_document_upload
from app.components.report_view import render_report_view
from src.agent.graph import run_agent_workflow
from src.input_layer.raw_store import save_raw_input


def match_public_building(address: str) -> dict[str, object] | None:
    path = "data/processed/ganak_building_clean.csv"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return None
    if df.empty:
        return None
    candidates = df[df["address_normalized"].astype(str).apply(lambda value: any(token in address for token in value.split()[-3:]))]
    row = candidates.iloc[0] if not candidates.empty else df.iloc[0]
    return {
        "area_m2": float(row["area_m2"]) if pd.notna(row["area_m2"]) else None,
        "approval_year": int(row["approval_year"]) if pd.notna(row["approval_year"]) else None,
        "violation_flag": bool(row["violation_flag"]),
        "main_usage": row["main_usage"],
        "building_register_checked": True,
        "non_residential_usage_flag": "주택" not in str(row["main_usage"]),
    }


def run_diagnosis(session_id: str, records: list[dict[str, object]], resolutions: dict[str, object] | None = None) -> dict[str, object]:
    result = run_agent_workflow({"session_id": session_id, "records": records, "resolutions": resolutions or {}})
    return dict(result)


def main() -> None:
    st.set_page_config(page_title="관악구 전세계약 위험진단 MVP", page_icon="🏠", layout="wide")
    st.title("관악구 전세계약 위험진단 MVP")
    st.caption("OCR이 틀려도 사용자 입력으로 보완해 진단까지 이어지는 입력 안정화 프로토타입")

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"S-{uuid4().hex[:8].upper()}"
    session_id = st.session_state.session_id

    with st.form("diagnosis_form"):
        basic = render_basic_input(st)
        checklist = render_document_checklist(st)
        submitted = st.form_submit_button("입력 저장", type="primary", use_container_width=True)

    upload_records = render_document_upload(st, session_id)

    if submitted:
        if "관악" not in basic["address"]:
            st.error("이번 MVP는 관악구 주소만 지원합니다.")
            return
        records: list[dict[str, object]] = []
        records.append(save_raw_input(session_id, "user_input", basic))
        records.append(save_raw_input(session_id, "user_checklist", checklist))
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
