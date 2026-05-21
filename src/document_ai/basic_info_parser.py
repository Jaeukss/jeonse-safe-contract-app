from __future__ import annotations

import re
from typing import Any

from .registry_parser import parse_money


HOUSING_KEYWORDS = {
    "아파트": ("아파트",),
    "오피스텔": ("오피스텔",),
    "연립다세대": ("연립", "다세대", "빌라"),
    "다가구": ("다가구", "단독주택"),
}


def _clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line or "").strip()
    return re.sub(r"^(?:주소|소재지|대지위치|도로명대지위치|임대차목적물)\s*[:：-]?\s*", "", line).strip()


def extract_address(text: str) -> str | None:
    raw = text or ""
    for line in raw.splitlines():
        if "서울" in line and ("관악구" in line or "강서구" in line):
            cleaned = _clean_line(line)
            match = re.search(
                r"(서울(?:특별시)?\s*(?:관악구|강서구)\s+[가-힣0-9]+동(?:\s+\d+(?:-\d+)?(?:번지)?)?(?:\s+[가-힣A-Za-z0-9\- ]{0,30})?)",
                cleaned,
            )
            return (match.group(1) if match else cleaned).strip()

    match = re.search(
        r"(서울(?:특별시)?\s*(?:관악구|강서구)\s+[가-힣0-9]+동(?:\s+\d+(?:-\d+)?(?:번지)?)?)",
        raw,
    )
    return match.group(1).strip() if match else None


def extract_housing_type(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text or "")
    for housing_type, keywords in HOUSING_KEYWORDS.items():
        if any(keyword in compact for keyword in keywords):
            return housing_type
    return None


def _money_after(labels: tuple[str, ...], text: str) -> int | None:
    labels_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{labels_pattern})\s*[:：-]?\s*([0-9,억천백십만원\s]+)", text or "")
    if not match:
        return None
    amount = parse_money(match.group(1))
    return amount or None


def extract_basic_info(text: str) -> dict[str, Any]:
    raw = text or ""
    area_match = re.search(
        r"(?:전용면적|전유면적|전유부분\s*면적|임대면적)\s*[:：-]?\s*(\d+(?:\.\d+)?)\s*(?:㎡|m2|제곱미터)?",
        raw,
        re.I,
    )
    floor_match = re.search(r"(?:층|해당층)\s*[:：-]?\s*(-?\d+)\s*층?", raw)
    if not floor_match:
        floor_match = re.search(r"(-?\d+)\s*층", raw)
    approval_match = re.search(
        r"(?:사용승인일|사용승인연도|사용승인|건축연도)\s*[:：-]?\s*(\d{4})",
        raw,
    )

    result = {
        "address": extract_address(raw),
        "housing_type": extract_housing_type(raw),
        "deposit": _money_after(("전세보증금", "임대보증금", "보증금"), raw),
        "monthly_rent": _money_after(("월세", "차임", "월차임"), raw),
        "area_m2": float(area_match.group(1)) if area_match else None,
        "floor": int(floor_match.group(1)) if floor_match else None,
        "built_year": int(approval_match.group(1)) if approval_match else None,
        "approval_year": int(approval_match.group(1)) if approval_match else None,
    }
    return {key: value for key, value in result.items() if value not in (None, "")}
