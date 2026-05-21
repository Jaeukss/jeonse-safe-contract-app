from __future__ import annotations

import json
import re
from typing import Any

from src.llm.openrouter_client import call_openrouter_with_fallback, has_openrouter_api_key

from .document_classifier import DocumentType


BASIC_INFO_SCHEMA_KEYS = (
    "address",
    "housing_type",
    "contract_stage",
    "deposit",
    "monthly_rent",
    "area_m2",
    "floor",
    "built_year",
    "approval_year",
    "registry_checked",
    "mortgage_flag",
    "mortgage_amount",
    "seizure_flag",
    "provisional_seizure_flag",
    "trust_flag",
    "leasehold_registration_flag",
    "building_register_checked",
    "main_usage",
    "violation_flag",
    "non_residential_usage_flag",
    "broker_explanation_checked",
    "rights_explained",
    "broker_signed",
)


def extract_with_llm_if_configured(document_type: DocumentType, text: str) -> dict[str, Any]:
    """Extract missing document fields with OpenRouter if a key is configured.

    The MVP still runs without an API key. If OPENROUTER_API_KEY is absent,
    the regex/OCR pipeline remains the only extraction path.
    """

    if not text.strip():
        return {}
    if not has_openrouter_api_key():
        return {}

    schema_keys = ", ".join(BASIC_INFO_SCHEMA_KEYS)
    messages = [
        {
            "role": "system",
            "content": (
                "You extract Korean real-estate contract and registry fields. "
                "Return JSON only. Do not guess. If a value is not visible, use null. "
                "Use only these keys: " + schema_keys
            ),
        },
        {
            "role": "user",
            "content": (
                f"document_type={document_type}\n"
                "Extract fields from this OCR/manual text. "
                "Money values must be KRW integers, area_m2 must be a number, "
                "booleans must be true/false/null.\n\n"
                f"{text[:12000]}"
            ),
        },
    ]
    content = call_openrouter_with_fallback(messages, temperature=0.0, max_tokens=1200)
    if not content:
        return {}
    return _parse_llm_json(content)


def _parse_llm_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S | re.I)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {key: value for key, value in parsed.items() if key in BASIC_INFO_SCHEMA_KEYS}


def merge_llm_fields(fields: dict[str, object], llm_fields: dict[str, Any]) -> dict[str, object]:
    for key, value in llm_fields.items():
        if key not in BASIC_INFO_SCHEMA_KEYS or value in (None, "", 0):
            continue
        if fields.get(key) in (None, "", 0):
            fields[key] = value
    return fields
