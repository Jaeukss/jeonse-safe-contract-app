from __future__ import annotations

import json
from pathlib import Path

from .query_templates import explanation_for


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "data" / "rag_official_sources.json"


def retrieve_evidence(keys: list[str]) -> list[dict[str, str]]:
    sources = []
    if SOURCE_PATH.exists():
        try:
            loaded = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                sources = loaded
            elif isinstance(loaded, dict):
                sources = loaded.get("sources", [])
        except json.JSONDecodeError:
            sources = []

    evidence: list[dict[str, str]] = []
    for key in keys:
        evidence.append(
            {
                "key": key,
                "summary": explanation_for(key),
                "title": sources[0].get("title", "공적 장부 확인") if sources else "공적 장부 확인",
                "url": sources[0].get("url", "https://www.iros.go.kr") if sources else "https://www.iros.go.kr",
            }
        )
    return evidence
