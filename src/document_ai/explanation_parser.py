from __future__ import annotations

import re

from .registry_parser import parse_money


def _money_after(labels: tuple[str, ...], text: str) -> int | None:
    labels_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{labels_pattern})\s*[:：-]?\s*([0-9,억천백십만원\s]+)", text or "")
    if not match:
        return None
    amount = parse_money(match.group(1))
    return amount or None


def parse_explanation_text(text: str) -> dict[str, object]:
    raw = text or ""
    return {
        "broker_explanation_checked": bool(raw.strip()),
        "deposit": _money_after(("전세보증금", "임대보증금", "보증금"), raw),
        "monthly_rent": _money_after(("월세", "차임", "월차임"), raw),
        "rights_explained": "권리관계" in raw or "근저당" in raw or "제한물권" in raw,
        "broker_signed": "공인중개사" in raw and ("서명" in raw or "날인" in raw),
    }
