from __future__ import annotations

import os
from typing import Any

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
    """Future extension point for API-key based structured JSON extraction.

    The MVP must run without an API key, so this function intentionally returns
    an empty result unless the user later enables an LLM extraction path.
    """

    if not text.strip():
        return {}
    if not os.getenv("OPENAI_API_KEY"):
        return {}
    if os.getenv("JEONSE_ENABLE_LLM_EXTRACTION") != "1":
        return {}

    # Keep the current MVP deterministic and free of mandatory network calls.
    # When high-accuracy extraction is enabled later, this function should call
    # a structured-output model and return only keys in BASIC_INFO_SCHEMA_KEYS.
    return {"llm_extraction_status": f"configured_but_not_implemented_for_{document_type}"}


def merge_llm_fields(fields: dict[str, object], llm_fields: dict[str, Any]) -> dict[str, object]:
    for key, value in llm_fields.items():
        if key not in BASIC_INFO_SCHEMA_KEYS or value in (None, "", 0):
            continue
        if fields.get(key) in (None, "", 0):
            fields[key] = value
    return fields
