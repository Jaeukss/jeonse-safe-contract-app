from __future__ import annotations

import re

from .registry_parser import parse_money


def parse_explanation_text(text: str) -> dict[str, object]:
    raw = text or ""
    deposit_match = re.search(r"보증금\s*[:：]?\s*([0-9,억만원\s]+)", raw)
    rent_match = re.search(r"(?:월세|차임)\s*[:：]?\s*([0-9,만원\s]+)", raw)
    return {
        "broker_explanation_checked": bool(raw.strip()),
        "deposit": parse_money(deposit_match.group(1)) if deposit_match else None,
        "monthly_rent": parse_money(rent_match.group(1)) if rent_match else None,
        "rights_explained": "권리관계" in raw or "근저당" in raw or "제한물권" in raw,
        "broker_signed": "공인중개사" in raw and ("서명" in raw or "날인" in raw),
    }
