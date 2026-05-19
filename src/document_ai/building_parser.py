from __future__ import annotations

import re


def parse_building_text(text: str) -> dict[str, object]:
    raw = text or ""
    usage_match = re.search(r"(?:주용도|용도)\s*[:：]?\s*([^\n\r]+)", raw)
    area_match = re.search(r"(?:전유부분|전용면적|면적)\s*[:：]?\s*(\d+(?:\.\d+)?)", raw)
    year_match = re.search(r"(?:사용승인일|사용승인연도|사용승인)\s*[:：]?\s*(\d{4})", raw)
    violation = "위반건축물" in raw or bool(re.search(r"위반\s*[:：]?\s*(?:Y|예|해당)", raw))
    main_usage = usage_match.group(1).strip() if usage_match else None
    return {
        "building_register_checked": bool(raw.strip()),
        "main_usage": main_usage,
        "area_m2": float(area_match.group(1)) if area_match else None,
        "approval_year": int(year_match.group(1)) if year_match else None,
        "violation_flag": violation,
        "non_residential_usage_flag": bool(main_usage and not any(word in main_usage for word in ["주택", "아파트", "다가구", "다세대"])),
    }
