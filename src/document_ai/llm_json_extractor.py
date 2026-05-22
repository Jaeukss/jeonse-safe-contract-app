from __future__ import annotations

import json
import re
from typing import Any

from src.llm.openrouter_client import call_openrouter, has_openrouter_api_key

from .document_classifier import DocumentType


BASIC_INFO_SCHEMA_KEYS = (
    "address",
    "housing_type",
    "contract_stage",
    "deposit",
    "monthly_rent",
    "area_m2",
    "floor",
    "room",
    "unit_dong",
    "built_year",
    "approval_year",
    "contract_type",
    "registry_checked",
    "mortgage_flag",
    "mortgage_amount",
    "seizure_flag",
    "provisional_seizure_flag",
    "trust_flag",
    "jeonse_right_flag",
    "leasehold_registration_flag",
    "ownership_transfer_recent_flag",
    "registry_warning_flag",
    "building_register_checked",
    "main_usage",
    "violation_flag",
    "non_residential_usage_flag",
    "broker_explanation_checked",
    "rights_explained",
    "broker_signed",
    "extraction_outlier_flag",
    "extraction_outlier_reasons",
    "manual_review_required",
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
                "You are a Korean real-estate contract and registry parsing verifier. "
                "Return a single JSON object only, with no markdown fence and no explanation. "
                "Do not guess. Use null for invisible or uncertain values. "
                "Use a flat object with only these keys: "
                + schema_keys
                + ". Treat extracted values as candidates, not facts. If floor is greater than 80 "
                "or below -5, omit floor and set extraction_outlier_flag=true with a reason. "
                "If an address is fragmented, normalize it only when Seoul plus Gwanak-gu or Gangseo-gu "
                "and a dong/road/building clue are visible. If money text is visible but deposit cannot "
                "be converted to KRW integer, set extraction_outlier_flag=true. "
                "For Korean money words, convert 금이억오천만원정 to 250000000 and 천오백만 to 15000000. "
                "For 1억 2,000 in a deposit context, treat 2,000 as 만원. "
                "Extract registry booleans only when visible: mortgage_flag for 근저당/채권최고액, "
                "seizure_flag for 압류, provisional_seizure_flag for 가압류, trust_flag for 신탁, "
                "jeonse_right_flag for 전세권/전세권설정, leasehold_registration_flag for 임차권등기, "
                "ownership_transfer_recent_flag for 소유권이전/소유권보존/접수일자, and "
                "registry_warning_flag for 가등기, 경매, 가처분, 처분금지가처분, 예고등기, "
                "소유권이전청구권. Do not infer contract_type unless deposit/monthly_rent evidence is visible."
            ),
        },
        {
            "role": "user",
            "content": (
                f"document_type={document_type}\n"
                "Verify and normalize fields from this OCR/manual text. "
                "Money values must be KRW integers, area_m2 must be a number, "
                "booleans must be true/false/null, extraction_outlier_reasons must be an array of strings. "
                "Never return impossible floor values such as 850 or -6 as floor; route them to outlier reasons.\n\n"
                f"{text[:12000]}"
            ),
        },
    ]
    content = call_openrouter(messages, temperature=0.0, max_tokens=1200)
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
    flattened = _flatten_llm_json(parsed)
    return {key: value for key, value in flattened.items() if key in BASIC_INFO_SCHEMA_KEYS}


def _flatten_llm_json(parsed: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(parsed)
    address = parsed.get("address")
    if isinstance(address, dict):
        parts = [
            address.get("city"),
            address.get("borough"),
            address.get("dong") or address.get("road_name"),
            address.get("building_name"),
        ]
        joined = " ".join(str(part).strip() for part in parts if part)
        if joined:
            flattened["address"] = joined
        for source_key, target_key in (("floor", "floor"), ("room", "room"), ("unit_dong", "unit_dong")):
            if source_key in address:
                flattened[target_key] = address.get(source_key)

    contract = parsed.get("contract")
    if isinstance(contract, dict):
        for key in ("deposit", "monthly_rent", "contract_type"):
            if key in contract:
                flattened[key] = contract.get(key)

    registry = parsed.get("registry")
    if isinstance(registry, dict):
        for key in (
            "registry_checked",
            "mortgage_flag",
            "mortgage_amount",
            "seizure_flag",
            "provisional_seizure_flag",
            "trust_flag",
            "jeonse_right_flag",
            "leasehold_registration_flag",
            "ownership_transfer_recent_flag",
            "registry_warning_flag",
        ):
            if key in registry:
                flattened[key] = registry.get(key)

    validation = parsed.get("validation_status")
    if isinstance(validation, dict):
        if "is_outlier" in validation:
            flattened["extraction_outlier_flag"] = bool(validation.get("is_outlier"))
            flattened["manual_review_required"] = bool(validation.get("is_outlier"))
        reason = validation.get("outlier_reason")
        reasons = validation.get("outlier_reasons")
        if reasons:
            flattened["extraction_outlier_reasons"] = reasons if isinstance(reasons, list) else [str(reasons)]
        elif reason:
            flattened["extraction_outlier_reasons"] = [str(reason)]
    return flattened


def merge_llm_fields(fields: dict[str, object], llm_fields: dict[str, Any]) -> dict[str, object]:
    for key, value in llm_fields.items():
        if key not in BASIC_INFO_SCHEMA_KEYS or value in (None, ""):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0:
            continue
        if key == "floor":
            try:
                if not -5 <= int(value) <= 80:
                    continue
            except (TypeError, ValueError):
                continue
        current = fields.get(key)
        current_missing = current is None or current == "" or (not isinstance(current, bool) and current == 0)
        if current_missing:
            fields[key] = value
    return fields
