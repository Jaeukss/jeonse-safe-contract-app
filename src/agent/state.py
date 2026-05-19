from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    records: list[dict[str, Any]]
    resolutions: dict[str, Any]
    snapshot: dict[str, Any]
    prediction: dict[str, Any]
    market: dict[str, Any]
    score: int
    signals: list[dict[str, Any]]
    blockers: list[str]
    grade: dict[str, str]
    evidence: list[dict[str, str]]
    actions: list[str]
    report_markdown: str
