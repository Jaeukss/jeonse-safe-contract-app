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

MONEY_CHARS = r"0-9,억천백십만원원금₩￦일이삼사오육칠팔구영공정\s"

MIN_REASONABLE_FLOOR = -5
MAX_REASONABLE_FLOOR = 80

ADDRESS_STOP_LABELS = (
    "주택유형",
    "주택 유형",
    "보증금",
    "전세보증금",
    "월세",
    "차임",
    "전용면적",
    "전유면적",
    "면적",
    "층",
    "사용승인",
    "건축연도",
    "계약금",
    "중도금",
    "잔금",
)


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


def _address_stop_pattern(compact: bool = False) -> re.Pattern[str]:
    labels = [re.escape(label.replace(" ", "") if compact else label) for label in ADDRESS_STOP_LABELS]
    separator = r"" if compact else r"\s+"
    return re.compile(rf"{separator}(?:{'|'.join(labels)})\s*[:：\-]?")


def _normalize_address(candidate: str) -> str:
    cleaned = _clean_line(candidate)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if " " not in cleaned:
        cleaned = re.sub(r"(서울(?:특별시|시)?)(관악구|강서구)", r"\1 \2 ", cleaned)
        cleaned = re.sub(r"(관악구|강서구)([가-힣0-9])", r"\1 \2", cleaned)
        cleaned = re.sub(r"([가-힣0-9]+동)(\d)", r"\1 \2", cleaned)
        cleaned = re.sub(r"(\d+(?:-\d+)?)([가-힣])", r"\1 \2", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;")


def extract_address(text: str) -> str | None:
    raw = text or ""
    label_stop = _address_stop_pattern()

    for line in raw.splitlines():
        if "서울" in line and ("관악구" in line or "강서구" in line):
            cleaned = label_stop.split(_clean_line(line))[0].strip()
            match = re.search(r"(서울(?:특별시|시)?\s*(?:관악구|강서구)\s+[^\n\r,;]{2,80})", cleaned)
            if match:
                return _normalize_address(match.group(1))
            return _normalize_address(cleaned)

    match = re.search(r"(서울(?:특별시|시)?\s*(?:관악구|강서구)\s+[^\n\r,;]{2,80})", raw)
    if match:
        return _normalize_address(label_stop.split(_clean_line(match.group(1)))[0])

    compact = re.sub(r"\s+", "", raw)
    compact_match = re.search(r"(서울(?:특별시|시)?(?:관악구|강서구).{2,80})", compact)
    if compact_match:
        compact_candidate = _address_stop_pattern(compact=True).split(compact_match.group(1))[0]
        return _normalize_address(compact_candidate)
    return None


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


def _has_money_trace(labels: tuple[str, ...], text: str) -> bool:
    labels_pattern = "|".join(re.escape(label) for label in labels)
    return bool(re.search(rf"(?:{labels_pattern})\s*[:：\-]?\s*[{MONEY_CHARS}]{{2,}}", text or "", re.I))


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


def _extract_floor_candidate(text: str) -> int | None:
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


def _floor_outlier_reason(floor: int | None) -> str | None:
    if floor is None:
        return None
    if floor < MIN_REASONABLE_FLOOR:
        return f"조건 A: 층수 오류 - {floor}층은 지하 {abs(MIN_REASONABLE_FLOOR)}층보다 낮아 OCR 결합 오류 가능성이 큽니다."
    if floor > MAX_REASONABLE_FLOOR:
        return f"조건 A: 층수 오류 - {floor}층은 MVP 검증 기준 {MAX_REASONABLE_FLOOR}층을 초과해 OCR 결합 오류 가능성이 큽니다."
    return None


def extract_floor(text: str) -> int | None:
    floor = _extract_floor_candidate(text)
    if _floor_outlier_reason(floor):
        return None
    return floor


def extract_room(text: str) -> str | None:
    raw = text or ""
    match = re.search(r"(?<!\d)(\d{1,4})\s*호(?!\d)", raw)
    if not match:
        return None
    return f"{match.group(1)}호"


def extract_unit_dong(text: str) -> str | None:
    raw = text or ""
    match = re.search(r"(?<!\d)(\d{1,4})\s*동(?![가-힣0-9])", raw)
    if not match:
        return None
    return f"{match.group(1)}동"


def extract_built_year(text: str) -> int | None:
    raw = text or ""
    match = re.search(
        r"(?:사용승인일|사용승인연도|사용승인|사용검사일|준공일|준공연도|건축연도|건축년도|승인일)\s*[:：\-]?\s*(\d{4})",
        raw,
    )
    if match:
        return int(match.group(1))
    return None


def infer_contract_type(text: str, deposit: int | None, monthly_rent: int | None) -> str | None:
    compact = _compact(text)
    if monthly_rent and monthly_rent > 0:
        return "반전세" if deposit and deposit > 0 else "월세"
    if "월세" in compact or "차임" in compact:
        return "월세" if not deposit else "반전세"
    if deposit or "전세" in compact:
        return "전세"
    return None


def extract_basic_info(text: str) -> dict[str, Any]:
    raw = text or ""
    outlier_reasons: list[str] = []
    monthly_rent = _money_after(("월세", "월차임", "차임", "월 임대료", "임대료"), raw)
    if monthly_rent is None and re.search(r"월세\s*(?:없음|0원|0\s*만원)", raw):
        monthly_rent = 0

    built_year = extract_built_year(raw)
    deposit_labels = ("전세보증금", "임대차보증금", "임대보증금", "임차보증금", "보증금", "전세금")
    deposit = _money_after(deposit_labels, raw)
    floor_candidate = _extract_floor_candidate(raw)
    floor_reason = _floor_outlier_reason(floor_candidate)
    if floor_reason:
        outlier_reasons.append(floor_reason)
    address = extract_address(raw)
    if not address and re.search(r"주소|소재지|부동산의\s*표시|임대차목적물|서울|관악구|강서구", raw):
        outlier_reasons.append("조건 B: 주소 불완전 - 주소 흔적은 있으나 서울시와 지원 구 단위 주소를 안정적으로 식별하지 못했습니다.")
    if deposit is None and _has_money_trace(deposit_labels, raw):
        outlier_reasons.append("조건 C: 금액 파싱 실패 - 보증금 기재 흔적은 있으나 정수형 원 단위 보증금으로 변환하지 못했습니다.")

    result = {
        "address": address,
        "housing_type": extract_housing_type(raw),
        "contract_stage": extract_contract_stage(raw),
        "deposit": deposit,
        "monthly_rent": monthly_rent,
        "area_m2": extract_area_m2(raw),
        "floor": None if floor_reason else floor_candidate,
        "room": extract_room(raw),
        "unit_dong": extract_unit_dong(raw),
        "built_year": built_year,
        "approval_year": built_year,
        "contract_type": infer_contract_type(raw, deposit, monthly_rent),
    }
    if outlier_reasons:
        result["extraction_outlier_flag"] = True
        result["extraction_outlier_reasons"] = outlier_reasons
        result["manual_review_required"] = True
    return {key: value for key, value in result.items() if value not in (None, "")}
