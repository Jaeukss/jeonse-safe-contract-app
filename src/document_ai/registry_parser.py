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

# 문서 전체가 권리관계 없음인 경우에만 전역 clear로 본다.
# "말소사항 포함", "압류 말소"처럼 일부 권리 말소 문구는 전역 clear로 처리하면 안 된다.
GLOBAL_CLEAR_PATTERNS = (
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


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


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


def _has_global_clear_phrase(compact: str) -> bool:
    return any(pattern in compact for pattern in GLOBAL_CLEAR_PATTERNS)


def _has_negative_flag(compact: str, keyword: str) -> bool:
    optional_suffix = r"(?:등기|권)?"
    return bool(
        re.search(rf"{keyword}{optional_suffix}(?:이|가|은|는)?(?:없음|없다|미해당|해당없음|미검출)", compact)
        or re.search(rf"{keyword}{optional_suffix}(?:해당)?없음", compact)
    )


def _explicit_active_table_flag(compact: str, field_name: str) -> bool | None:
    # 샘플/테스트 PDF에 포함된 추출용 필드 표를 우선 신뢰한다.
    # 예: has_active_attachment false, has_active_mortgage true
    match = re.search(rf"{re.escape(field_name)}(true|false)", compact, re.I)
    if match:
        return match.group(1).lower() == "true"
    return None


def _appears_cancelled(compact: str, *keywords: str) -> bool:
    for keyword in keywords:
        # 같은 항목 안에서 바로 말소/해제되는 경우만 취소로 본다.
        # 등기부 전체 요약에 있는 "압류 말소됨" 문구가 앞쪽의 전세권/근저당권까지
        # 끌고 가서 False로 만드는 것을 방지하기 위해 탐색 범위를 짧게 제한한다.
        if re.search(rf"(?:\d+번)?{keyword}(?:등기|권)?(?:말소|해제|취하|해지)", compact):
            return True
        if re.search(rf"{keyword}.{{0,40}}(?:말소됨|해제됨)", compact):
            return True
    return False


def _flag(compact: str, *keywords: str, allow_cancelled: bool = False) -> bool:
    if any(_has_negative_flag(compact, keyword) for keyword in keywords):
        return False
    if not any(keyword in compact for keyword in keywords):
        return False
    if not allow_cancelled and _appears_cancelled(compact, *keywords):
        return False
    return True


def _money_after_label(text: str, *labels: str) -> int:
    raw = text or ""
    amounts: list[int] = []
    labels_pattern = "|".join(re.escape(label) for label in labels)

    for match in re.finditer(rf"(?:{labels_pattern})\s*[:：\-]?\s*([{MONEY_CHARS}]{{2,60}})", raw, re.I):
        amount = parse_money(match.group(1))
        if amount:
            amounts.append(amount)

    for line in raw.splitlines():
        compact_line = line.replace(" ", "")
        if not any(label.replace(" ", "") in compact_line for label in labels):
            continue
        amount = parse_money(line)
        if amount and amount >= 1_000_000:
            amounts.append(amount)

    # 등기부에서는 변경계약이 뒤에 나오므로 마지막으로 발견한 채권최고액을 우선한다.
    return amounts[-1] if amounts else 0


def _active_seizure_flag(compact: str) -> bool:
    explicit = _explicit_active_table_flag(compact, "has_active_attachment")
    if explicit is not None:
        return explicit

    seizure_compact = compact.replace("가압류", "")
    if _has_negative_flag(seizure_compact, "압류"):
        return False
    if "압류" not in seizure_compact:
        return False

    # "3번 압류 말소"처럼 말소된 압류만 있는 샘플은 현재 위험 신호로 보지 않는다.
    if _appears_cancelled(seizure_compact, "압류") and not re.search(r"말소되지않은압류(?:있음|존재)", seizure_compact):
        return False
    return True


def _active_mortgage_flag(compact: str, mortgage_amount: int) -> bool:
    explicit = _explicit_active_table_flag(compact, "has_active_mortgage")
    if explicit is not None:
        return explicit
    if mortgage_amount > 0:
        return True
    return _flag(compact, "근저당권", "근저당", "채권최고액")


def parse_registry_text(text: str) -> dict[str, object]:
    raw = text or ""
    compact = _compact(raw)
    global_clear = _has_global_clear_phrase(compact)

    mortgage_amount = _money_after_label(raw, "채권최고액", "채권 최고액")
    mortgage_flag = _active_mortgage_flag(compact, mortgage_amount)

    warning_flag = any(keyword in compact for keyword in REGISTRY_WARNING_KEYWORDS)
    ownership_transfer = any(keyword in compact for keyword in OWNERSHIP_TRANSFER_KEYWORDS)

    if global_clear:
        mortgage_flag = False
        mortgage_amount = 0
        seizure_flag = False
        provisional_seizure_flag = False
        trust_flag = False
        jeonse_right_flag = False
        leasehold_registration_flag = False
        registry_warning_flag = False
    else:
        seizure_flag = _active_seizure_flag(compact)
        provisional_seizure_flag = _flag(compact, "가압류")
        trust_flag = _flag(compact, "신탁등기", "신탁", "수탁자")
        jeonse_right_flag = _flag(compact, "전세권", "전세권설정")
        leasehold_registration_flag = _flag(compact, "임차권등기")
        registry_warning_flag = warning_flag

    return {
        "registry_checked": bool(raw.strip()),
        "mortgage_flag": mortgage_flag,
        "mortgage_amount": mortgage_amount,
        "seizure_flag": seizure_flag,
        "provisional_seizure_flag": provisional_seizure_flag,
        "trust_flag": trust_flag,
        "jeonse_right_flag": jeonse_right_flag,
        "leasehold_registration_flag": leasehold_registration_flag,
        "ownership_transfer_recent_flag": ownership_transfer,
        "registry_warning_flag": registry_warning_flag,
    }
