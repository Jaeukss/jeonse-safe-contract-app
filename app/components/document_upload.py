from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any

from app.components.basic_input import apply_basic_defaults
from app.components.document_review import apply_document_review_defaults
from src.document_ai.upload_handler import handle_text_input, handle_upload


PREFILL_SOURCE_PRIORITY = {
    "explanation_ocr": 0,
    "manual_correction": 1,
    "registry_ocr": 2,
    "building_ocr": 3,
}

REVIEW_PREFILL_SOURCE_PRIORITY = {
    "registry_ocr": 0,
    "manual_correction": 1,
    "explanation_ocr": 2,
    "building_ocr": 3,
    "public_building_data": 4,
}

BASIC_PREFILL_FIELDS = {
    "address": "주소",
    "housing_type": "주택유형",
    "deposit": "보증금",
    "monthly_rent": "월세",
    "area_m2": "전용면적",
    "floor": "층",
    "built_year": "건축연도",
    "contract_stage": "계약 단계",
}

REVIEW_PREFILL_FIELDS = {
    "registry_checked": "등기부등본 확인",
    "mortgage_flag": "근저당권",
    "mortgage_amount": "채권최고액",
    "seizure_flag": "압류",
    "provisional_seizure_flag": "가압류",
    "trust_flag": "신탁등기",
    "jeonse_right_flag": "전세권",
    "leasehold_registration_flag": "임차권등기",
    "ownership_transfer_recent_flag": "소유권 변동 단서",
    "registry_warning_flag": "주의 권리관계",
    "building_register_checked": "건축물대장 확인",
    "violation_flag": "위반건축물",
    "non_residential_usage_flag": "주용도 비주택",
    "broker_explanation_checked": "확인설명서 수령",
    "rights_explained": "권리관계 설명",
    "broker_signed": "공인중개사 서명/날인",
    "senior_deposit_checked": "선순위 임차보증금 확인",
}

BOOLEAN_REVIEW_FIELDS = {
    "registry_checked",
    "mortgage_flag",
    "seizure_flag",
    "provisional_seizure_flag",
    "trust_flag",
    "jeonse_right_flag",
    "leasehold_registration_flag",
    "ownership_transfer_recent_flag",
    "registry_warning_flag",
    "building_register_checked",
    "violation_flag",
    "non_residential_usage_flag",
    "broker_explanation_checked",
    "rights_explained",
    "broker_signed",
    "senior_deposit_checked",
}


def _has_prefill_value(field: str, value: Any) -> bool:
    if value in (None, ""):
        return False
    if field == "monthly_rent":
        return isinstance(value, (int, float)) or str(value).strip() != ""
    if field in {"deposit", "area_m2", "floor", "built_year"}:
        try:
            return float(value) != 0
        except (TypeError, ValueError):
            return False
    return True


def _has_review_prefill_value(field: str, value: Any) -> bool:
    if value in (None, ""):
        return False
    if field in BOOLEAN_REVIEW_FIELDS:
        return isinstance(value, bool)
    if field == "mortgage_amount":
        try:
            return int(float(value)) > 0
        except (TypeError, ValueError):
            return False
    return True


def _field_value(record: dict[str, Any], field: str) -> Any:
    data = record.get("data", {})
    if field == "built_year":
        return data.get("built_year") or data.get("approval_year")
    return data.get(field)


def build_basic_prefill(records: list[dict[str, Any]]) -> dict[str, Any]:
    prefill: dict[str, Any] = {}
    ordered = sorted(records, key=lambda item: PREFILL_SOURCE_PRIORITY.get(str(item.get("source")), 99))
    for record in ordered:
        for field in BASIC_PREFILL_FIELDS:
            value = _field_value(record, field)
            if _has_prefill_value(field, value) and field not in prefill:
                prefill[field] = value
    return prefill


def build_document_review_prefill(records: list[dict[str, Any]]) -> dict[str, Any]:
    prefill: dict[str, Any] = {}
    ordered = sorted(records, key=lambda item: REVIEW_PREFILL_SOURCE_PRIORITY.get(str(item.get("source")), 99))
    for record in ordered:
        for field in REVIEW_PREFILL_FIELDS:
            value = _field_value(record, field)
            if _has_review_prefill_value(field, value) and field not in prefill:
                prefill[field] = value
    return prefill


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 1.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _editable_prefill(st: Any, prefill: dict[str, Any]) -> dict[str, Any]:
    edited: dict[str, Any] = {}
    col1, col2 = st.columns(2)
    with col1:
        if "address" in prefill:
            edited["address"] = st.text_input("추출 주소", value=str(prefill["address"]), key="prefill_address")
        if "housing_type" in prefill:
            edited["housing_type"] = st.text_input("추출 주택유형", value=str(prefill["housing_type"]), key="prefill_housing_type")
        if "contract_stage" in prefill:
            edited["contract_stage"] = st.text_input("추출 계약 단계", value=str(prefill["contract_stage"]), key="prefill_contract_stage")
    with col2:
        if "deposit" in prefill:
            edited["deposit"] = st.number_input("추출 보증금", min_value=0, step=10_000_000, value=_to_int(prefill["deposit"]), key="prefill_deposit")
        if "monthly_rent" in prefill:
            edited["monthly_rent"] = st.number_input("추출 월세", min_value=0, step=50_000, value=_to_int(prefill["monthly_rent"]), key="prefill_monthly_rent")
        if "area_m2" in prefill:
            edited["area_m2"] = st.number_input("추출 전용면적(㎡)", min_value=1.0, step=1.0, value=_to_float(prefill["area_m2"]), key="prefill_area_m2")
        if "floor" in prefill:
            edited["floor"] = st.number_input("추출 층", min_value=-5, max_value=80, step=1, value=_to_int(prefill["floor"]), key="prefill_floor")
        if "built_year" in prefill:
            edited["built_year"] = st.number_input("추출 건축연도", min_value=1900, max_value=2100, step=1, value=_to_int(prefill["built_year"], 2005), key="prefill_built_year")
    return edited


def _seed_prefill_widgets(st: Any, prefill: dict[str, Any], digest: str) -> None:
    if st.session_state.get("prefill_widget_digest") == digest:
        return
    widget_values = {
        "prefill_address": str(prefill.get("address", "")),
        "prefill_housing_type": str(prefill.get("housing_type", "")),
        "prefill_contract_stage": str(prefill.get("contract_stage", "")),
        "prefill_deposit": _to_int(prefill.get("deposit")),
        "prefill_monthly_rent": _to_int(prefill.get("monthly_rent")),
        "prefill_area_m2": _to_float(prefill.get("area_m2")),
        "prefill_floor": _to_int(prefill.get("floor")),
        "prefill_built_year": _to_int(prefill.get("built_year"), 2005),
    }
    for key, value in widget_values.items():
        st.session_state[key] = value
    st.session_state["prefill_widget_digest"] = digest


def _format_prefill(prefill: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for field, label in BASIC_PREFILL_FIELDS.items():
        if field in prefill:
            rows.append({"항목": label, "추출값": str(prefill[field])})
    return rows


def _format_review_value(value: Any) -> str:
    if value is True:
        return "있음/확인함"
    if value is False:
        return "없음/확인 못함"
    if isinstance(value, (int, float)):
        return f"{int(value):,}"
    return str(value)


def _format_review_prefill(prefill: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for field, label in REVIEW_PREFILL_FIELDS.items():
        if field in prefill:
            rows.append({"항목": label, "추출값": _format_review_value(prefill[field])})
    return rows


def _upload_result(st: Any, session_id: str, file: Any) -> dict[str, Any]:
    data = file.getvalue()
    digest = hashlib.sha256(data).hexdigest()[:16]
    cache_key = f"{session_id}:{file.name}:{len(data)}:{digest}"
    cache = st.session_state.setdefault("uploaded_document_results", {})
    if cache_key not in cache:
        cache[cache_key] = handle_upload(session_id, BytesIO(data), file.name)
    result = dict(cache[cache_key])
    result["_cache_key"] = cache_key
    return result


def _format_ocr_error(error: Any) -> str:
    message = str(error or "").strip()
    if not message:
        return ""
    hints = {
        "tesseract executable not found": "Tesseract 실행 파일이 설치되어 있지 않습니다.",
        "tesseract language pack missing": "Tesseract 한국어/영어 언어팩이 설치되어 있지 않습니다.",
        "pdf render failed": "스캔 PDF를 이미지로 변환하는 과정에서 실패했습니다.",
        "image open failed": "이미지 파일을 열 수 없습니다.",
        "tesseract returned empty text": "OCR 엔진이 이미지를 읽었지만 텍스트를 찾지 못했습니다.",
    }
    for key, hint in hints.items():
        if key in message:
            return f"{hint} 원인: {message}"
    return f"OCR 처리 중 문제가 발생했습니다. 원인: {message}"


def _format_outlier_warning(record: dict[str, Any]) -> str:
    data = record.get("data", {})
    if not data.get("extraction_outlier_flag"):
        return ""
    reasons = data.get("extraction_outlier_reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    if not reasons:
        return "문서 추출값에 이상값이 감지되어 기본정보에서 직접 확인해야 합니다."
    return " / ".join(str(reason) for reason in reasons)


def _render_ocr_review(st: Any, session_id: str, result: dict[str, Any], filename: str) -> dict[str, Any]:
    cache_key = str(result["_cache_key"])
    reviewed = st.session_state.setdefault("reviewed_document_results", {})
    active_result = reviewed.get(cache_key, result)
    raw_text = str(active_result.get("text") or result.get("text") or "")
    text_key = f"ocr_review_text_{hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:12]}"

    with st.expander(f"{filename} OCR 원문 확인·수정", expanded=False):
        st.caption("OCR이 주소, 보증금, 권리관계 등을 잘못 읽었으면 여기서 고친 뒤 다시 분석하세요.")
        edited_text = st.text_area("OCR 원문", value=raw_text, height=180, key=text_key)
        cols = st.columns([1, 2])
        if cols[0].button("수정한 텍스트로 다시 분석", key=f"reanalyze_{text_key}", use_container_width=True):
            reviewed[cache_key] = handle_text_input(session_id, edited_text, filename=f"edited_{filename}.txt")
            st.session_state.pop("auto_prefill_digest", None)
            st.session_state.pop("review_prefill_digest", None)
            st.success("수정한 OCR 텍스트를 다시 분석했습니다. 추출값이 기본정보와 보완입력에 다시 반영됩니다.")
            active_result = reviewed[cache_key]
        cols[1].caption("API 키 없이 동작하는 MVP라 OCR 원문 보정이 가장 안정적인 안전장치입니다.")

    return active_result


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
        st.caption("추출값이 틀리면 여기서 먼저 고친 뒤 기본정보에 반영하세요. 월세가 없으면 0원으로 둡니다.")
        _seed_prefill_widgets(st, prefill, digest)
        edited_prefill = _editable_prefill(st, prefill)
        if st.button("문서 추출값/수정값으로 기본정보 덮어쓰기", use_container_width=True):
            changed = apply_basic_defaults(st, edited_prefill, overwrite=True)
            st.session_state["auto_prefill_digest"] = digest
            if changed:
                st.success("문서 추출값을 기본정보 입력칸에 반영했습니다.")
            else:
                st.info("이미 기본정보 입력칸에 같은 값이 들어 있습니다.")
            if hasattr(st, "rerun"):
                st.rerun()


def _render_review_prefill_controls(st: Any, prefill: dict[str, Any]) -> None:
    if not prefill:
        st.info("문서에서 권리관계/확인정보로 바로 반영할 항목은 아직 추출되지 않았습니다. 아래 보완입력에서 직접 선택할 수 있습니다.")
        return

    digest = hashlib.sha256(json.dumps(prefill, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if st.session_state.get("review_prefill_digest") != digest:
        changed = apply_document_review_defaults(st, prefill, overwrite=True)
        st.session_state["review_prefill_digest"] = digest
        if changed:
            st.success("문서에서 추출한 권리관계/확인정보를 보완입력에 자동 반영했습니다. 값이 다르면 아래에서 직접 수정하세요.")

    with st.expander("문서에서 추출한 권리관계/확인정보", expanded=True):
        st.table(_format_review_prefill(prefill))
        st.caption("이 값들은 아래 ‘OCR 결과 확인 및 보완 입력’에 기본값으로 들어갑니다. 사용자가 수정한 값이 최종 진단에 반영됩니다.")
        if st.button("문서 추출값으로 보완입력 다시 덮어쓰기", use_container_width=True):
            changed = apply_document_review_defaults(st, prefill, overwrite=True)
            st.session_state["review_prefill_digest"] = digest
            if changed:
                st.success("문서 추출값을 보완입력에 다시 반영했습니다.")
            else:
                st.info("이미 보완입력에 같은 값이 들어 있습니다.")
            if hasattr(st, "rerun"):
                st.rerun()


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
            active_result = _render_ocr_review(st, session_id, result, file.name)
            records.append(active_result["record"])
            st.caption(
                f"{file.name}: {active_result['document_type']} / {active_result['method']} / OCR 신뢰도 {active_result['record'].get('ocr_confidence', 0)}"
            )
            ocr_error = _format_ocr_error(active_result.get("ocr_error"))
            if ocr_error:
                st.warning(
                    f"{file.name} OCR 경고: {ocr_error} "
                    "스캔 PDF/이미지라면 아래 OCR 원문 보정란 또는 직접 붙여넣기로 보완해주세요."
                )
            if active_result["pii_blocked"]:
                st.warning(f"{file.name}에서 개인정보 마스킹 잔여 가능성이 있어 RAG/LLM 경로를 차단했습니다.")
            outlier_warning = _format_outlier_warning(active_result["record"])
            if outlier_warning:
                st.warning(
                    f"{file.name} 추출값 확인 필요: {outlier_warning} "
                    "자동 반영값을 그대로 믿지 말고 기본정보 입력란에서 직접 수정하세요."
                )

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
    _render_review_prefill_controls(st, build_document_review_prefill(records))
    return records
