from __future__ import annotations

from html import escape
from typing import Any


def action_list(signals: list[dict[str, Any]]) -> list[str]:
    actions = []
    for signal in signals:
        key = signal["key"]
        if key == "trust":
            actions.append("신탁원부와 수탁자 동의서를 확인하세요.")
        elif key == "seizure":
            actions.append("압류·가압류 말소 전까지 계약 진행을 보류하세요.")
        elif key == "mortgage":
            actions.append("채권최고액과 잔금 전 말소 조건을 계약서 특약에 반영하세요.")
        elif key == "jeonse_ratio":
            actions.append("HUG 전세보증금반환보증 가능성과 보증금 조정을 확인하세요.")
        elif key == "violation":
            actions.append("정부24 또는 세움터에서 건축물대장을 재발급하세요.")
    actions.append("계약 전과 잔금 전 등기부등본과 건축물대장을 다시 확인하세요.")
    return list(dict.fromkeys(actions))[:6]


def render_html_report(grade: str, score: int, signals: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> str:
    items = "".join(
        f"<li><strong>{escape(signal['title'])}</strong>: {escape(signal['detail'])}</li>"
        for signal in signals
    )
    sources = "".join(
        f"<li><a href=\"{escape(item['official_url'])}\">{escape(item['title'])}</a> - {escape(item['provider'])}</li>"
        for item in evidence
    )
    return (
        "<section>"
        f"<h1>전세계약 위험 진단 리포트</h1>"
        f"<p>위험등급: <strong>{escape(grade)}</strong> / 점수: {score}</p>"
        f"<h2>위험 신호</h2><ul>{items or '<li>중대한 위험 신호 낮음</li>'}</ul>"
        f"<h2>공식 근거</h2><ul>{sources}</ul>"
        "</section>"
    )
