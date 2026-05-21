from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from src.input_layer.raw_store import save_raw_input

from .document_classifier import classify_document
from .extract_fields import extract_fields
from .pii_masking import has_unmasked_pii, mask_pii
from .text_extractor import extract_text_with_diagnostics


ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = ROOT / "data" / "raw" / "user_uploads"


SOURCE_BY_TYPE = {
    "registry": "registry_ocr",
    "building": "building_ocr",
    "explanation": "explanation_ocr",
    "unknown": "registry_ocr",
}


def handle_upload(session_id: str, file_obj: BinaryIO, filename: str) -> dict[str, object]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    data = file_obj.read()
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    saved_path = UPLOAD_DIR / f"{session_id}_{Path(filename).name}"
    saved_path.write_bytes(data)

    extraction = extract_text_with_diagnostics(data, filename=filename)
    text = extraction.text
    confidence = extraction.confidence
    method = extraction.method
    masked_text, pii_counts = mask_pii(text)
    pii_blocked = has_unmasked_pii(masked_text)
    document_type = classify_document(masked_text)
    fields = extract_fields(document_type, masked_text) if not pii_blocked else {"pii_blocked": True}
    record = save_raw_input(
        session_id=session_id,
        source=SOURCE_BY_TYPE[document_type],  # type: ignore[arg-type]
        data=fields,
        file_name=filename,
        ocr_confidence=confidence,
    )
    return {
        "record": record,
        "document_type": document_type,
        "method": method,
        "ocr_error": extraction.ocr_error,
        "text": masked_text,
        "pii_counts": pii_counts,
        "pii_blocked": pii_blocked,
    }


def handle_text_input(session_id: str, text: str, filename: str = "pasted_document.txt") -> dict[str, object]:
    masked_text, pii_counts = mask_pii(text or "")
    pii_blocked = has_unmasked_pii(masked_text)
    document_type = classify_document(masked_text)
    fields = extract_fields(document_type, masked_text) if not pii_blocked else {"pii_blocked": True}
    record = save_raw_input(
        session_id=session_id,
        source=SOURCE_BY_TYPE[document_type],  # type: ignore[arg-type]
        data=fields,
        file_name=filename,
        ocr_confidence=0.98,
    )
    return {
        "record": record,
        "document_type": document_type,
        "method": "pasted_text",
        "text": masked_text,
        "pii_counts": pii_counts,
        "pii_blocked": pii_blocked,
    }
