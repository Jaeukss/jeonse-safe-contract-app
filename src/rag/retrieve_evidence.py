from __future__ import annotations

import json
from pathlib import Path

from .query_templates import explanation_for


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "data" / "rag_official_sources.json"

SOURCE_BY_SIGNAL = {
    "jeonse_ratio": "molit_jeonse_fraud_checklist",
    "rent_gap_rate": "molit_jeonse_fraud_checklist",
    "market_insufficient": "molit_jeonse_fraud_checklist",
    "market_low_count": "molit_jeonse_fraud_checklist",
    "mortgage": "real_estate_registration_act",
    "mortgage_burden": "hug_deposit_return_guarantee",
    "seizure": "real_estate_registration_act",
    "provisional_seizure": "real_estate_registration_act",
    "trust": "real_estate_registration_act",
    "leasehold_registration": "housing_lease_protection_act",
    "violation": "building_registry_guide",
    "non_residential": "building_registry_guide",
    "registry_unchecked": "real_estate_registration_act",
    "building_unchecked": "building_registry_guide",
    "explanation_unchecked": "property_confirmation_form",
    "senior_deposit": "housing_lease_protection_act",
}


def _load_sources() -> list[dict[str, object]]:
    if not SOURCE_PATH.exists():
        return []
    try:
        loaded = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    if isinstance(loaded, dict):
        sources = loaded.get("sources", [])
        return [item for item in sources if isinstance(item, dict)]
    return []


def _source_url(source: dict[str, object]) -> str:
    for key in ("official_url", "mobile_apply_url", "leaflet_url", "download_page_url", "url"):
        value = source.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    return "https://www.iros.go.kr"


def retrieve_evidence(keys: list[str]) -> list[dict[str, str]]:
    sources = _load_sources()
    by_id = {source.get("id"): source for source in sources}
    fallback = sources[0] if sources else {}

    evidence: list[dict[str, str]] = []
    for key in keys:
        source = by_id.get(SOURCE_BY_SIGNAL.get(key), fallback)
        evidence.append(
            {
                "key": key,
                "summary": explanation_for(key),
                "title": str(source.get("required_item") or source.get("title") or "공식 자료 확인"),
                "url": _source_url(source),
            }
        )
    return evidence
