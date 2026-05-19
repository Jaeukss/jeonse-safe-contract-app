from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentSignals:
    mortgage_flag: bool = False
    mortgage_amount: int = 0
    seizure_flag: bool = False
    provisional_seizure_flag: bool = False
    trust_flag: bool = False
    leasehold_registration_flag: bool = False
    ownership_transfer_flag: bool = False
    violation_flag: bool = False
    extracted_chars: int = 0


def parse_korean_money(text: str) -> int:
    normalized = re.sub(r"[\s,]", "", text or "")
    total = 0.0
    eok = re.search(r"(\d+(?:\.\d+)?)억", normalized)
    man = re.search(r"(\d+(?:\.\d+)?)만", normalized)
    if eok:
        total += float(eok.group(1)) * 100_000_000
    if man:
        total += float(man.group(1)) * 10_000
    if not total:
        digits = re.search(r"\d{7,}", normalized)
        if digits:
            total = float(digits.group(0))
    return int(total)


def extract_document_signals(text: str) -> DocumentSignals:
    raw = text or ""
    compact = re.sub(r"\s+", "", raw)
    clear = bool(re.search(r"없음|해당없음|말소완료|기재사항없음", compact))
    amount_match = re.search(r"(채권최고액|근저당)[^0-9억만]*(\d+(?:[,.]\d+)?\s*억?\s*\d*(?:[,.]\d+)?\s*만?원?)", raw)

    return DocumentSignals(
        mortgage_flag=not clear and bool(re.search(r"근저당|채권최고액", compact)),
        mortgage_amount=parse_korean_money(amount_match.group(2)) if amount_match else 0,
        seizure_flag=not clear and bool(re.search(r"(?<!가)압류", compact)),
        provisional_seizure_flag=not clear and "가압류" in compact,
        trust_flag=not clear and "신탁" in compact,
        leasehold_registration_flag=not clear and "임차권등기" in compact,
        ownership_transfer_flag=bool(re.search(r"소유권이전|최근소유권", compact)),
        violation_flag=not clear and bool(re.search(r"위반건축물|위반건축", compact)),
        extracted_chars=len(raw.strip()),
    )
