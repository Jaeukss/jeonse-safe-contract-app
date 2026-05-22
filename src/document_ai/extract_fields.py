from __future__ import annotations

from .building_parser import parse_building_text
from .basic_info_parser import extract_basic_info
from .document_classifier import DocumentType
from .explanation_parser import parse_explanation_text
from .llm_json_extractor import extract_with_llm_if_configured, merge_llm_fields
from .registry_parser import parse_registry_text


REGISTRY_FALLBACK_KEYWORDS = (
    "근저당",
    "채권최고액",
    "압류",
    "가압류",
    "신탁",
    "전세권",
    "임차권등기",
    "소유권",
    "가등기",
    "경매",
    "가처분",
    "을구",
    "갑구",
)


def _is_missing(value: object) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, bool):
        return False
    return value == 0


def _merge_missing_fields(target: dict[str, object], source: dict[str, object]) -> None:
    for key, value in source.items():
        if not _is_missing(value) and _is_missing(target.get(key)):
            target[key] = value


def extract_fields(document_type: DocumentType, text: str) -> dict[str, object]:
    basic = extract_basic_info(text)
    compact = (text or "").replace(" ", "")

    if document_type == "registry":
        fields = parse_registry_text(text)
    elif document_type == "building":
        fields = parse_building_text(text)
    elif document_type == "explanation":
        fields = parse_explanation_text(text)
    else:
        fields = {"unclassified_text_chars": len(text or "")}

    if document_type != "registry" and any(keyword in compact for keyword in REGISTRY_FALLBACK_KEYWORDS):
        _merge_missing_fields(fields, parse_registry_text(text))
    if document_type != "building" and any(keyword in compact for keyword in ("건축물대장", "위반건축물", "사용승인", "주용도")):
        _merge_missing_fields(fields, parse_building_text(text))
    if document_type != "explanation" and any(keyword in compact for keyword in ("중개대상물", "확인설명서", "보증금", "월세", "차임")):
        _merge_missing_fields(fields, parse_explanation_text(text))

    _merge_missing_fields(fields, basic)
    fields = merge_llm_fields(fields, extract_with_llm_if_configured(document_type, text))
    if document_type == "building":
        fields["building_register_checked"] = bool((text or "").strip())
    return fields
