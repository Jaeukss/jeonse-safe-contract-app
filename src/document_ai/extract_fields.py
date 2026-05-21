from __future__ import annotations

from .building_parser import parse_building_text
from .basic_info_parser import extract_basic_info
from .document_classifier import DocumentType
from .explanation_parser import parse_explanation_text
from .llm_json_extractor import extract_with_llm_if_configured, merge_llm_fields
from .registry_parser import parse_registry_text


def extract_fields(document_type: DocumentType, text: str) -> dict[str, object]:
    basic = extract_basic_info(text)
    if document_type == "registry":
        fields = parse_registry_text(text)
    elif document_type == "building":
        fields = parse_building_text(text)
    elif document_type == "explanation":
        fields = parse_explanation_text(text)
    else:
        fields = {"unclassified_text_chars": len(text or "")}

    compact = (text or "").replace(" ", "")
    if document_type != "building" and any(keyword in compact for keyword in ("건축물대장", "위반건축물", "사용승인", "주용도")):
        for key, value in parse_building_text(text).items():
            if fields.get(key) in (None, "", 0):
                fields[key] = value
    if document_type != "explanation" and any(keyword in compact for keyword in ("중개대상물", "확인설명서", "보증금", "월세", "차임")):
        for key, value in parse_explanation_text(text).items():
            if fields.get(key) in (None, "", 0):
                fields[key] = value

    for key, value in basic.items():
        if fields.get(key) in (None, "", 0):
            fields[key] = value
    fields = merge_llm_fields(fields, extract_with_llm_if_configured(document_type, text))
    if document_type == "building":
        fields["building_register_checked"] = bool((text or "").strip())
    return fields
