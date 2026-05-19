from __future__ import annotations

import re


def parse_money(text: str) -> int:
    compact = re.sub(r"[\s,]", "", text or "")
    total = 0.0
    eok = re.search(r"(\d+(?:\.\d+)?)억", compact)
    man = re.search(r"(\d+(?:\.\d+)?)만", compact)
    if eok:
        total += float(eok.group(1)) * 100_000_000
    if man:
        total += float(man.group(1)) * 10_000
    if not total:
        digits = re.search(r"\d{7,}", compact)
        if digits:
            total = float(digits.group(0))
    return int(total)


def parse_registry_text(text: str) -> dict[str, object]:
    compact = re.sub(r"\s+", "", text or "")
    clear = bool(re.search(r"해당없음|말소|기재사항없음|권리관계없음", compact))
    amount_match = re.search(r"채권최고액[^0-9억만]*(\d[\d,]*(?:억)?\s*\d*[\d,]*(?:만)?원?)", text or "")
    return {
        "registry_checked": bool(text.strip()),
        "mortgage_flag": False if clear else bool(re.search(r"근저당권|채권최고액", compact)),
        "mortgage_amount": parse_money(amount_match.group(1)) if amount_match else 0,
        "seizure_flag": False if clear else bool(re.search(r"(?<!가)압류", compact)),
        "provisional_seizure_flag": False if clear else "가압류" in compact,
        "trust_flag": False if clear else "신탁" in compact or "수탁자" in compact,
        "leasehold_registration_flag": False if clear else "임차권등기" in compact,
        "ownership_transfer_recent_flag": bool(re.search(r"소유권이전|접수일자", compact)),
    }
