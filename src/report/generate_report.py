from __future__ import annotations

from datetime import datetime
from typing import Any

from src.report.explanation_templates import render_signal_explanation


def money(value: int | float | None) -> str:
    amount = int(value or 0)
    eok, rest = divmod(amount, 100_000_000)
    man = rest // 10_000
    if eok and man:
        return f"{eok}억 {man:,}만원"
    if eok:
        return f"{eok}억원"
    return f"{man:,}만원"


def generate_markdown_report(result: dict[str, Any]) -> str:
    snapshot = result["snapshot"]
    market = result["market"]
    grade = result["grade"]
    signals = result["signals"]
    evidence = result["evidence"]
    lines = [
        "# 전세계약 위험진단 리포트",
        "",
        f"- 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 주소: {snapshot.get('address', '확인 불가')}",
        f"- 보증금: {money(snapshot.get('deposit'))}",
        f"- 주택유형: {snapshot.get('housing_type', '확인 불가')}",
        "",
        f"## 전세계약 위험등급: {grade['grade']}",
        "",
        grade["message"],
        "",
        "## 시세 지표",
        "",
        f"- 예측 적정 전세가: {money(market.get('predicted_rent_price'))}",
        f"- 예측 매매가: {money(market.get('predicted_sale_price'))}",
        f"- 주택가격 보조값: {money(market.get('official_house_price'))}",
        f"- 산출 방식: {market.get('model_note', '확인 불가')}",
        f"- 전세가율: {market.get('jeonse_ratio')}%",
        f"- 시세괴리율: {market.get('rent_gap_rate')}%",
        f"- 유사 거래 수: {market.get('similar_transaction_count')}건",
        f"- 시세 신뢰도: {market.get('market_confidence')}",
        "",
        "## 핵심 위험 신호",
        "",
    ]
    if signals:
        for signal in signals:
            lines.append(f"- **{signal['title']}**: {signal['detail']}")
            lines.append(f"  - 확인 이유: {render_signal_explanation(signal)}")
    else:
        lines.append("- 현재 확인된 정보 기준 큰 위험 신호는 적습니다.")
    lines.extend(["", "## 다음 행동", ""])
    for action in result["actions"]:
        lines.append(f"- {action}")
    lines.extend(["", "## 참고 근거", ""])
    for item in evidence:
        lines.append(f"- [{item['title']}]({item['url']}): {item['summary']}")
    lines.append("")
    lines.append("> 본 리포트는 MVP 위험진단이며 법률 판단이 아닙니다. 불명확한 조건은 전문가 확인을 권장합니다.")
    return "\n".join(lines)


def recommended_actions(signals: list[dict[str, Any]], blockers: list[str]) -> list[str]:
    if blockers:
        return ["주소, 보증금, 전용면적 등 필수 정보를 먼저 보완하세요."]
    actions = ["계약 직전 등기부등본과 건축물대장 최신본을 다시 확인하세요."]
    keys = {signal["key"] for signal in signals}
    if "mortgage" in keys or "mortgage_burden" in keys:
        actions.append("채권최고액과 보증금을 합산해 추정 매매가 대비 비율을 확인하세요.")
    if "trust" in keys:
        actions.append("수탁자 동의 및 임대 권한을 문서로 확인하세요.")
    if "seizure" in keys or "provisional_seizure" in keys:
        actions.append("압류·가압류 말소 가능 여부를 전문가와 확인하세요.")
    if "senior_deposit" in keys:
        actions.append("다가구 선순위 임차보증금 총액을 임대인과 중개사에게 확인하세요.")
    if "registry_unchecked" in keys:
        actions.append("인터넷등기소에서 등기부등본 최신본을 발급받으세요.")
    return actions
