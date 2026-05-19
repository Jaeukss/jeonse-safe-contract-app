from __future__ import annotations

from typing import Any

from src.document_ai.upload_handler import handle_upload


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
            result = handle_upload(session_id, file, file.name)
            records.append(result["record"])
            st.caption(
                f"{file.name}: {result['document_type']} / {result['method']} / OCR 신뢰도 {result['record'].get('ocr_confidence', 0)}"
            )
            if result["pii_blocked"]:
                st.warning(f"{file.name}에서 개인정보 마스킹 잔여 가능성이 있어 RAG/LLM 경로를 차단했습니다.")
    return records
