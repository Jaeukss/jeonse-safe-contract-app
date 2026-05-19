from __future__ import annotations

from .building_parser import parse_building_text
from .document_classifier import DocumentType
from .explanation_parser import parse_explanation_text
from .registry_parser import parse_registry_text


def extract_fields(document_type: DocumentType, text: str) -> dict[str, object]:
    if document_type == "registry":
        return parse_registry_text(text)
    if document_type == "building":
        return parse_building_text(text)
    if document_type == "explanation":
        return parse_explanation_text(text)
    return {"unclassified_text_chars": len(text or "")}
