from __future__ import annotations

import re


PII_PATTERNS = {
    "resident_registration_number": re.compile(r"\b\d{6}-[1-4]\d{6}\b"),
    "phone": re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "account": re.compile(r"\b\d{2,6}-\d{2,6}-\d{3,8}\b"),
}


def mask_pii(text: str) -> tuple[str, dict[str, int]]:
    masked = text or ""
    counts: dict[str, int] = {}
    for key, pattern in PII_PATTERNS.items():
        masked, count = pattern.subn(f"[MASKED_{key.upper()}]", masked)
        counts[key] = count
    return masked, counts


def has_unmasked_pii(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in PII_PATTERNS.values())
