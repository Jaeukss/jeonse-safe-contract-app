from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any

from app.components.basic_input import apply_basic_defaults
from src.document_ai.upload_handler import handle_text_input, handle_upload


BASIC_PREFILL_FIELDS = {
    "address": "주소",
    "housing_type": "주택유형",
    "deposit": "보증금",
    "monthly_rent": "월세",
    "area_m2": "전용면적",
    "floor": "층",
    "built_year": "건축연도",
}


def _field_value(record: dict[str, Any], field: str) -> Any:
    data = record.get("data", {})
    if field == "built_year":
        return data.get("built_year") or data.get("approval_year")
    return data.get(field)


def build_basic_prefill(records: list[dict[str, Any]]) -> dict[str, Any]:
    prefill: dict[str, Any] = {}
    priority = ["explanation_ocr", "building_ocr", "registry_ocr"]
    ordered = sorted(records, key=lambda item: priority.index(item["source"]) if item.get("source") in priority else len(priority))
    for record in ordered:
        for field in BASIC_PREFILL_FIELDS:
            value = _field_value(record, field)
            if value not in (None, "", 0) and field not in prefill:
                prefill[field] = value
    return prefill


def _format_prefill(prefill: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for field, label in BASIC_PREFILL_FIELDS.items():
        if field in prefill:
            rows.append({"항목": label, "추출값": str(prefill[field])})
    return rows


def _upload_result(st: Any, session_id: str, file: Any) -> dict[str, Any]:
    data = file.getvalue()
    digest = hashlib.sha256(data).hexdigest()[:16]
    cache_key = f"{session_id}:{file.name}:{len(data)}:{digest}"
    cache = st.session_state.setdefault("uploaded_document_results", {})
    if cache_key not in cache:
        cache[cache_key] = handle_upload(session_id, BytesIO(data), file.name)
    return cache[cache_key]


def _render_prefill_controls(st: Any, prefill: dict[str, Any]) -> None:
    if not prefill:
        st.info("문서에서 기본정보로 바로 반영할 항목은 아직 추출되지 않았습니다. 필요한 값은 아래 기본정보에 직접 입력할 수 있습니다.")
        return

    digest = hashlib.sha256(json.dumps(prefill, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if st.session_state.get("auto_prefill_digest") != digest:
        changed = apply_basic_defaults(st, prefill, overwrite=True)
        st.session_state["auto_prefill_digest"] = digest
        if changed:
            st.success("문서에서 추출한 기본정보를 자동 반영했습니다. 값이 다르면 기본정보에서 직접 수정하세요.")

    with st.expander("문서에서 추출한 기본정보", expanded=True):
        st.table(_format_prefill(prefill))
        if st.button("문서 추출값으로 기본정보 덮어쓰기", use_container_width=True):
            apply_basic_defaults(st, prefill, overwrite=True)
            st.success("문서 추출값을 기본정보에 반영했습니다.")


def render_document_upload(st: Any, session_id: str) -> list[dict[str, Any]]:
    st.subheader("2. 문서 업로드")
    uploaded_files = st.file_uploader(
        "등기부등본, 건축물대장, 중개대상물 확인설명서 PDF/TXT/이미지",
        type=["pdf", "txt", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    records = []
    if uploaded_files:
        for file in uploaded_files:
            result = _upload_result(st, session_id, file)
            records.append(result["record"])
            st.caption(
                f"{file.name}: {result['document_type']} / {result['method']} / OCR 신뢰도 {result['record'].get('ocr_confidence', 0)}"
            )
            if result["pii_blocked"]:
                st.warning(f"{file.name}에서 개인정보 마스킹 잔여 가능성이 있어 RAG/LLM 경로를 차단했습니다.")

    pasted_text = st.text_area("문서 텍스트 직접 붙여넣기", height=110, placeholder="OCR이 잘 안 되면 등기부등본/건축물대장/확인설명서에서 보이는 내용을 붙여넣으세요.")
    if st.button("붙여넣은 문서 분석", use_container_width=True, disabled=not pasted_text.strip()):
        text_key = hashlib.sha256(pasted_text.encode("utf-8")).hexdigest()[:16]
        cache = st.session_state.setdefault("pasted_document_results", {})
        if text_key not in cache:
            cache[text_key] = handle_text_input(session_id, pasted_text)
        records.append(cache[text_key]["record"])

    for result in st.session_state.get("pasted_document_results", {}).values():
        record = result["record"]
        if record not in records:
            records.append(record)

    _render_prefill_controls(st, build_basic_prefill(records))
    return records
