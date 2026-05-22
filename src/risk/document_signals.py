from __future__ import annotations

from typing import Any


LABELS = {
    "mortgage_flag": "근저당권",
    "seizure_flag": "압류",
    "provisional_seizure_flag": "가압류",
    "trust_flag": "신탁등기",
    "jeonse_right_flag": "전세권등기",
    "leasehold_registration_flag": "임차권등기",
    "ownership_transfer_recent_flag": "소유권 변동 단서",
    "registry_warning_flag": "등기상 주의/특이사항",
    "violation_flag": "위반건축물",
    "non_residential_usage_flag": "주용도 비주택",
}


def status_from_value(value: Any, checked: bool) -> str:
    if value is True:
        return "검출"
    if value is False and checked:
        return "미검출"
    return "미확인"


def build_document_signal_cards(fields: dict[str, Any]) -> list[dict[str, Any]]:
    registry_checked = bool(fields.get("registry_checked"))
    building_checked = bool(fields.get("building_register_checked") or fields.get("public_building_matched"))
    cards = []
    for key, label in LABELS.items():
        checked = building_checked if key in {"violation_flag", "non_residential_usage_flag"} else registry_checked
        cards.append(
            {
                "key": key,
                "label": label,
                "status": status_from_value(fields.get(key), checked),
                "source": "OCR/사용자 입력 병합",
                "confidence": fields.get(f"{key}_confidence"),
            }
        )
    return cards
