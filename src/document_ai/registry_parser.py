from __future__ import annotations

import re


HANGUL_DIGITS = {
    "영": 0,
    "공": 0,
    "일": 1,
    "이": 2,
    "삼": 3,
    "사": 4,
    "오": 5,
    "육": 6,
    "칠": 7,
    "팔": 8,
    "구": 9,
}

HANGUL_SMALL_UNITS = {"십": 10, "백": 100, "천": 1000}
MONEY_CHARS = r"금₩￦0-9,억천백십만원원정일이삼사오육칠팔구영공\s"

CLEAR_PATTERNS = (
    "해당없음",
    "말소",
    "기재사항없음",
    "권리관계없음",
    "을구사항없음",
    "을구기재사항없음",
)

REGISTRY_WARNING_KEYWORDS = (
    "가등기",
    "경매",
    "임의경매",
    "강제경매",
    "가처분",
    "처분금지가처분",
    "예고등기",
    "소유권이전청구권",
)

OWNERSHIP_TRANSFER_KEYWORDS = (
    "소유권이전",
    "소유권보존",
    "소유권일부이전",
    "접수일자",
)


def _parse_hangul_under_10000(text: str) -> int:
    total = 0
    current = 0
    for char in text:
        if char in HANGUL_DIGITS:
            current = HANGUL_DIGITS[char]
        elif char in HANGUL_SMALL_UNITS:
            total += (current or 1) * HANGUL_SMALL_UNITS[char]
            current = 0
    return total + current


def _parse_hangul_money(compact: str) -> int:
    if not any(char in compact for char in set(HANGUL_DIGITS) | set(HANGUL_SMALL_UNITS) | {"억", "만"}):
        return 0

    total = 0
    rest = compact
    if "억" in rest:
        before, rest = rest.split("억", 1)
        total += (_parse_hangul_under_10000(before) or 1) * 100_000_000
    if "만" in rest:
        before, _after = rest.split("만", 1)
        total += (_parse_hangul_under_10000(before) or 1) * 10_000
    return total


def parse_money(text: str) -> int:
    compact = re.sub(r"[\s,₩￦]", "", text or "")
    compact = compact.replace("원", "").replace("금", "").replace("정", "")

    pure_digits = re.fullmatch(r"\d{6,}", compact)
    if pure_digits:
        return int(compact)

    total = 0.0
    eok = re.search(r"(\d+(?:\.\d+)?)억", compact)
    if eok:
        total += float(eok.group(1)) * 100_000_000
        compact = compact[eok.end() :]

    unit_patterns = (
        (r"(\d+(?:\.\d+)?)천만", 10_000_000),
        (r"(\d+(?:\.\d+)?)백만", 1_000_000),
        (r"(\d+(?:\.\d+)?)십만", 100_000),
        (r"(\d+(?:\.\d+)?)만", 10_000),
        (r"(\d+(?:\.\d+)?)천", 10_000_000),
    )
    for pattern, unit in unit_patterns:
        while True:
            match = re.search(pattern, compact)
            if not match:
                break
            total += float(match.group(1)) * unit
            compact = compact[: match.start()] + compact[match.end() :]

    if total and re.fullmatch(r"\d{1,4}", compact):
        total += float(compact) * 10_000

    if not total:
        hangul_amount = _parse_hangul_money(compact)
        if hangul_amount:
            total = float(hangul_amount)

    if not total:
        digits = re.search(r"\d{7,}", compact)
        if digits:
            total = float(digits.group(0))
    return int(total)


def _has_clear_phrase(compact: str) -> bool:
    return any(pattern in compact for pattern in CLEAR_PATTERNS)


def _has_negative_flag(compact: str, keyword: str) -> bool:
    optional_suffix = r"(?:등기|권)?"
    return bool(
        re.search(rf"{keyword}{optional_suffix}(?:이|가|은|는)?(?:없음|없다|미해당|말소)", compact)
        or re.search(rf"{keyword}{optional_suffix}(?:해당)?없음", compact)
    )


def _flag(compact: str, *keywords: str) -> bool:
    if any(_has_negative_flag(compact, keyword) for keyword in keywords):
        return False
    for keyword in keywords:
        if keyword not in compact:
            continue
        negative_patterns = [
            rf"{keyword}(?:이|가)?없음",
            rf"{keyword}(?:해당)?없음",
            rf"{keyword}미해당",
            rf"{keyword}말소",
        ]
        if any(re.search(pattern, compact) for pattern in negative_patterns):
            continue
        return True
    return False


def _money_after_label(text: str, *labels: str) -> int:
    raw = text or ""
    for line in raw.splitlines():
        compact_line = line.replace(" ", "")
        if not any(label.replace(" ", "") in compact_line for label in labels):
            continue
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*[:：\-]?\s*([{MONEY_CHARS}]{{2,}})", line)
            if match:
                amount = parse_money(match.group(1))
                if amount:
                    return amount
        amount = parse_money(line)
        if amount:
            return amount

    labels_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{labels_pattern})\s*[:：\-]?\s*([{MONEY_CHARS}]{{2,40}})", raw, re.I)
    if match:
        return parse_money(match.group(1))
    return 0


def parse_registry_text(text: str) -> dict[str, object]:
    raw = text or ""
    compact = re.sub(r"\s+", "", raw)
    clear = _has_clear_phrase(compact)
    seizure_compact = compact.replace("가압류", "")

    mortgage_amount = _money_after_label(raw, "채권최고액", "채권 최고액", "근저당권")
    mortgage_flag = _flag(compact, "근저당권", "근저당", "채권최고액") or mortgage_amount > 0

    warning_flag = any(keyword in compact for keyword in REGISTRY_WARNING_KEYWORDS)
    ownership_transfer = any(keyword in compact for keyword in OWNERSHIP_TRANSFER_KEYWORDS)

    return {
        "registry_checked": bool(raw.strip()),
        "mortgage_flag": False if clear else mortgage_flag,
        "mortgage_amount": mortgage_amount,
        "seizure_flag": False if clear else _flag(seizure_compact, "압류"),
        "provisional_seizure_flag": False if clear else _flag(compact, "가압류"),
        "trust_flag": False if clear else _flag(compact, "신탁등기", "신탁", "수탁자"),
        "jeonse_right_flag": False if clear else _flag(compact, "전세권", "전세권설정"),
        "leasehold_registration_flag": False if clear else _flag(compact, "임차권등기"),
        "ownership_transfer_recent_flag": ownership_transfer,
        "registry_warning_flag": False if clear else warning_flag,
    }
