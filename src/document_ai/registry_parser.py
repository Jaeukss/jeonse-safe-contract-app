from __future__ import annotations

import re


def parse_money(text: str) -> int:
    compact = re.sub(r"[\s,]", "", text or "").replace("원", "")
    total = 0.0
    eok = re.search(r"(\d+(?:\.\d+)?)억", compact)
    if eok:
        total += float(eok.group(1)) * 100_000_000
        compact = compact[eok.end() :]

    # OCR/manual text often arrives as "2억 4천만원" or "7천만원".
    # Match the most specific unit first so "4천만원" is not counted again
    # by the shorter "천" fallback.
    unit_patterns = (
        (r"(\d+(?:\.\d+)?)천만", 10_000_000),
        (r"(\d+(?:\.\d+)?)백만", 1_000_000),
        (r"(\d+(?:\.\d+)?)십만", 100_000),
        (r"(\d+(?:\.\d+)?)만", 10_000),
        (r"(\d+(?:\.\d+)?)천", 10_000_000),
    )
    for pattern, unit in unit_patterns:
        match = re.search(pattern, compact)
        if match:
            total += float(match.group(1)) * unit
            break

    if not total:
        digits = re.search(r"\d{7,}", compact)
        if digits:
            total = float(digits.group(0))
    return int(total)


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


def parse_registry_text(text: str) -> dict[str, object]:
    compact = re.sub(r"\s+", "", text or "")
    clear = bool(re.search(r"해당없음|말소|기재사항없음|권리관계없음", compact))
    amount_match = re.search(r"채권최고액[^0-9억천백십만]*(\d[\d,]*(?:억)?\s*\d*[\d,]*(?:천|백|십)?(?:만)?원?)", text or "")
    provisional_seizure = False if clear else _flag(compact, "가압류")
    seizure_compact = compact.replace("가압류", "")
    return {
        "registry_checked": bool(text.strip()),
        "mortgage_flag": False if clear else _flag(compact, "근저당권", "채권최고액"),
        "mortgage_amount": parse_money(amount_match.group(1)) if amount_match else 0,
        "seizure_flag": False if clear else _flag(seizure_compact, "압류"),
        "provisional_seizure_flag": provisional_seizure,
        "trust_flag": False if clear else _flag(compact, "신탁등기", "신탁", "수탁자"),
        "leasehold_registration_flag": False if clear else _flag(compact, "임차권등기"),
        "ownership_transfer_recent_flag": bool(re.search(r"소유권이전|접수일자", compact)),
    }
