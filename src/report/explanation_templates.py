from __future__ import annotations

from src.rag.query_templates import explanation_for


def render_signal_explanation(signal: dict[str, object]) -> str:
    key = str(signal.get("key", ""))
    return explanation_for(key)
