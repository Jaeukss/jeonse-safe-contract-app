from __future__ import annotations

from typing import Any


BOOLEAN_FIELDS = {
    "mortgage_flag",
    "seizure_flag",
    "provisional_seizure_flag",
    "trust_flag",
    "jeonse_right_flag",
    "leasehold_registration_flag",
    "ownership_transfer_recent_flag",
    "registry_warning_flag",
    "violation_flag",
    "non_residential_usage_flag",
}


def is_unknown(value: Any) -> bool:
    return value is None or value == "" or value == "unknown"


def value_conflicts(field: str, left: Any, right: Any) -> bool:
    if is_unknown(left) or is_unknown(right):
        return False
    if field == "area_m2":
        try:
            left_num = float(left)
            right_num = float(right)
        except (TypeError, ValueError):
            return str(left).strip() != str(right).strip()
        if not left_num or not right_num:
            return False
        return abs(left_num - right_num) / max(left_num, right_num) > 0.03
    if field in {"deposit", "monthly_rent", "mortgage_amount"}:
        try:
            return abs(int(left) - int(right)) > 10000
        except (TypeError, ValueError):
            return str(left).strip() != str(right).strip()
    if field in BOOLEAN_FIELDS:
        return bool(left) != bool(right)
    return str(left).strip() != str(right).strip()


def detect_conflicts(candidates: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for field, values in candidates.items():
        known = [item for item in values if not is_unknown(item.get("value"))]
        for index, left in enumerate(known):
            for right in known[index + 1 :]:
                if value_conflicts(field, left.get("value"), right.get("value")):
                    conflicts.append(
                        {
                            "field": field,
                            "left": left,
                            "right": right,
                            "recommended": left if left.get("confidence", 0) >= right.get("confidence", 0) else right,
                            "reason": "출처별 값이 다릅니다. 진단에 사용할 값을 사용자가 확정해야 합니다.",
                        }
                    )
    return conflicts
