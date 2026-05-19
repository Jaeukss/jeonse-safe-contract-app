from __future__ import annotations

from collections import defaultdict
from typing import Any

from .detect_conflict import detect_conflicts, is_unknown
from .schema import FieldValue


SOURCE_CONFIDENCE = {
    "user_input": 1.0,
    "user_checklist": 0.75,
    "registry_ocr": 0.72,
    "building_ocr": 0.72,
    "explanation_ocr": 0.7,
    "public_building_data": 0.86,
    "market_data": 0.82,
}

FIELD_PRIORITY = {
    "mortgage_flag": ["registry_ocr", "user_checklist"],
    "mortgage_amount": ["registry_ocr", "user_checklist"],
    "seizure_flag": ["registry_ocr", "user_checklist"],
    "provisional_seizure_flag": ["registry_ocr", "user_checklist"],
    "trust_flag": ["registry_ocr", "user_checklist"],
    "leasehold_registration_flag": ["registry_ocr", "user_checklist"],
    "violation_flag": ["public_building_data", "building_ocr", "user_checklist"],
    "non_residential_usage_flag": ["public_building_data", "building_ocr", "user_checklist"],
    "deposit": ["explanation_ocr", "user_input"],
    "area_m2": ["public_building_data", "building_ocr", "user_input"],
}


def collect_candidates(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        source = record["source"]
        confidence = float(record.get("ocr_confidence") or SOURCE_CONFIDENCE.get(source, 0.6))
        for field, value in record.get("data", {}).items():
            candidates[field].append(
                {
                    "value": value,
                    "source": source,
                    "confidence": confidence,
                    "input_id": record.get("input_id"),
                }
            )
    return dict(candidates)


def choose_candidate(field: str, values: list[dict[str, Any]]) -> dict[str, Any] | None:
    known = [item for item in values if not is_unknown(item.get("value"))]
    if not known:
        return None
    priority = FIELD_PRIORITY.get(field)
    if priority:
        for source in priority:
            for item in known:
                if item["source"] == source:
                    return item
    return sorted(known, key=lambda item: item.get("confidence", 0), reverse=True)[0]


def merge_records(records: list[dict[str, Any]], resolutions: dict[str, Any] | None = None) -> tuple[dict[str, FieldValue], list[dict[str, Any]]]:
    resolutions = resolutions or {}
    candidates = collect_candidates(records)
    conflicts = detect_conflicts(candidates)
    conflict_fields = {conflict["field"] for conflict in conflicts}
    fields: dict[str, FieldValue] = {}

    for field, values in candidates.items():
        if field in resolutions:
            fields[field] = FieldValue(value=resolutions[field], source="user_resolution", confidence=1.0, status="confirmed")
            continue
        if field in conflict_fields:
            recommended = next(conflict["recommended"] for conflict in conflicts if conflict["field"] == field)
            fields[field] = FieldValue(
                value=recommended.get("value"),
                source=recommended.get("source"),
                confidence=float(recommended.get("confidence", 0)),
                status="conflict",
            )
            continue
        selected = choose_candidate(field, values)
        if selected:
            fields[field] = FieldValue(
                value=selected["value"],
                source=selected["source"],
                confidence=float(selected.get("confidence", 0)),
                status="confirmed",
            )
        else:
            fields[field] = FieldValue()

    return fields, conflicts
