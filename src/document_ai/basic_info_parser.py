from __future__ import annotations

import re
from typing import Any

from .registry_parser import parse_money


HOUSING_KEYWORDS = {
    "아파트": ("아파트", "apt"),
    "오피스텔": ("오피스텔", "officetel"),
    "연립다세대": ("연립", "다세대", "빌라", "연립주택", "다세대주택"),
    "다가구": ("다가구", "단독주택", "단독", "다중주택"),
}

CONTRACT_STAGE_KEYWORDS = (
    ("잔금 전", ("잔금", "잔금일", "말소 조건", "보증금 지급 전")),
    ("입주 직전", ("입주", "전입", "확정일자", "이사")),
    ("계약 당일", ("계약일", "계약 당일", "계약 체결")),
    ("계약 전 확인", ("계약 전", "사전 확인", "확인설명서", "중개대상물")),
    ("매물 검토", ("매물", "임장", "검토")),
)

MONEY_CHARS = r"0-9,억천백십만원원금₩\s"


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _clean_line(line: str) -> str:
    cleaned = re.sub(r"\s+", " ", line or "").strip()
    cleaned = re.sub(
        r"^(?:주소|소재지|건물소재지|대지위치|도로명대지위치|임대차목적물|부동산의\s*표시)\s*[:：\-]?\s*",
        "",
        cleaned,
    )
    return cleaned.strip(" ,;")


def extract_address(text: str) -> str | None:
    raw = text or ""
    label_stop = re.compile(
        r"\s+(?:주택유형|보증금|전세보증금|월세|차임|전용면적|전유면적|면적|층|사용승인|건축연도)\s*[:：\-]?"
    )

    for line in raw.splitlines():
        if "서울" in line and ("관악구" in line or "강서구" in line):
            cleaned = label_stop.split(_clean_line(line))[0].strip()
            match = re.search(r"(서울(?:특별시|시)?\s*(?:관악구|강서구)\s+[^\n\r,;]{2,80})", cleaned)
            if match:
                return match.group(1).strip()
            return cleaned

    match = re.search(r"(서울(?:특별시|시)?\s*(?:관악구|강서구)\s+[^\n\r,;]{2,80})", raw)
    if not match:
        return None
    return label_stop.split(_clean_line(match.group(1)))[0].strip()


def extract_housing_type(text: str) -> str | None:
    compact = _compact(text).lower()
    for housing_type, keywords in HOUSING_KEYWORDS.items():
        if any(keyword.lower() in compact for keyword in keywords):
            return housing_type
    return None


def extract_contract_stage(text: str) -> str | None:
    compact = _compact(text)
    for stage, keywords in CONTRACT_STAGE_KEYWORDS:
        if any(keyword in compact for keyword in keywords):
            return stage
    return None


def _money_after(labels: tuple[str, ...], text: str) -> int | None:
    labels_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{labels_pattern})\s*[:：\-]?\s*([{MONEY_CHARS}]+)", text or "", re.I)
    if not match:
        return None
    amount = parse_money(match.group(1))
    return amount or None


def extract_area_m2(text: str) -> float | None:
    raw = text or ""
    patterns = (
        r"(?:전용면적|전유면적|전유부분\s*면적|임대면적|계약면적)\s*[:：\-]?\s*(\d+(?:\.\d+)?)\s*(?:㎡|m2|m²|제곱미터)?",
        r"(?<!대지)(?<!연)면적\s*[:：\-]?\s*(\d+(?:\.\d+)?)\s*(?:㎡|m2|m²|제곱미터)?",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, re.I)
        if match:
            return float(match.group(1))
    return None


def extract_floor(text: str) -> int | None:
    raw = text or ""
    patterns = (
        r"(?:해당층|소재층|목적물\s*층|전유부분\s*층|층수|층)\s*[:：\-]?\s*(?:지상|제)?\s*(-?\d+)\s*층?",
        r"(?:지상|제)\s*(-?\d+)\s*층",
        r"(?<!\d)(-?\d+)\s*층(?!\d)",
    )
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return int(match.group(1))
    return None


def extract_built_year(text: str) -> int | None:
    raw = text or ""
    match = re.search(
        r"(?:사용승인일|사용승인연도|사용승인|사용검사일|준공일|준공연도|건축연도|건축년도|승인일)\s*[:：\-]?\s*(\d{4})",
        raw,
    )
    if match:
        return int(match.group(1))
    return None


def extract_basic_info(text: str) -> dict[str, Any]:
    raw = text or ""
    monthly_rent = _money_after(("월세", "월차임", "차임", "월 임대료", "임대료"), raw)
    if monthly_rent is None and re.search(r"월세\s*(?:없음|0원|0\s*만원)", raw):
        monthly_rent = 0

    built_year = extract_built_year(raw)
    result = {
        "address": extract_address(raw),
        "housing_type": extract_housing_type(raw),
        "contract_stage": extract_contract_stage(raw),
        "deposit": _money_after(("전세보증금", "임대차보증금", "임대보증금", "임차보증금", "보증금", "전세금"), raw),
        "monthly_rent": monthly_rent,
        "area_m2": extract_area_m2(raw),
        "floor": extract_floor(raw),
        "built_year": built_year,
        "approval_year": built_year,
    }
    return {key: value for key, value in result.items() if value not in (None, "")}
