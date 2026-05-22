from __future__ import annotations

from datetime import datetime
from typing import Any

from src.report.explanation_templates import render_signal_explanation


OFFICIAL_LINKS = {
    "registry": {
        "title": "대법원 인터넷등기소",
        "url": "https://www.iros.go.kr",
    },
    "building": {
        "title": "정부24 건축물대장 등본·초본 발급(열람)",
        "url": "https://m.gov.kr/mw/AA020InfoCappView.do?CappBizCD=15000000098&HighCtgCD=A09005&tp_seq=01",
    },
    "eais": {
        "title": "세움터",
        "url": "https://www.eais.go.kr",
    },
    "hug": {
        "title": "모바일HUG 전세보증금반환보증",
        "url": "https://onestop.khug.or.kr/webView/webBiz/apply/goods001",
    },
    "move_in": {
        "title": "정부24 전입신고",
        "url": "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016&tp_seq=01",
    },
    "fixed_date": {
        "title": "인터넷등기소 확정일자",
        "url": "https://www.iros.go.kr",
    },
    "safehome": {
        "title": "국토교통부 안심전세포털",
        "url": "https://www.molit.go.kr/2023safehome/main.jsp",
    },
}


def official_check_links() -> list[dict[str, str]]:
    return list(OFFICIAL_LINKS.values())


def _link(key: str) -> str:
    item = OFFICIAL_LINKS[key]
    return f"[{item['title']}]({item['url']})"


def _append_unique(actions: list[str], action: str) -> None:
    if action not in actions:
        actions.append(action)


def money(value: int | float | None) -> str:
    amount = int(value or 0)
    eok, rest = divmod(amount, 100_000_000)
    man = rest // 10_000
    if eok and man:
        return f"{eok}억 {man:,}만원"
    if eok:
        return f"{eok}억원"
    return f"{man:,}만원"


def _append_evidence_cards(lines: list[str], evidence: list[dict[str, Any]]) -> None:
    lines.extend(["", "## RAG 근거 카드", ""])
    if not evidence:
        lines.append("- 현재 위험 신호에 연결된 RAG 근거 카드가 없습니다.")
        return
    for item in evidence:
        key = item.get("key", "evidence")
        title = item.get("title", "공식 자료 확인")
        summary = item.get("summary", "계약 전 원문 문서와 최신 공적 장부 확인이 필요합니다.")
        url = item.get("url", "")
        lines.append(f"### Evidence Card · {key}")
        lines.append("")
        lines.append(f"- 근거 자료: [{title}]({url})" if url else f"- 근거 자료: {title}")
        lines.append(f"- 요약: {summary}")
        lines.append("- 확인 방식: OCR/사용자 입력 병합값과 공식 확인 자료를 함께 대조")
        lines.append("")


def generate_markdown_report(result: dict[str, Any]) -> str:
    snapshot = result["snapshot"]
    market = result["market"]
    grade = result["grade"]
    signals = result["signals"]
    evidence = result.get("evidence", [])
    lines = [
        "# 전세계약 위험진단 리포트",
        "",
        f"- 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 주소: {snapshot.get('address', '확인 불가')}",
        f"- 건물 동: {snapshot.get('unit_dong') or '확인 불가'}",
        f"- 호수: {snapshot.get('room') or '확인 불가'}",
        f"- 계약유형: {snapshot.get('contract_type') or '확인 불가'}",
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
    _append_evidence_cards(lines, evidence)
    lines.extend(["", "## 공식 확인 링크", ""])
    for item in official_check_links():
        lines.append(f"- [{item['title']}]({item['url']})")
    lines.extend(["", "## 참고 근거", ""])
    for item in evidence:
        lines.append(f"- [{item['title']}]({item['url']}): {item['summary']}")
    lines.append("")
    lines.append("> 본 리포트는 MVP 위험진단이며 법률 판단이 아닙니다. 불명확한 조건은 전문가 확인을 권장합니다.")
    return "\n".join(lines)


def recommended_actions(signals: list[dict[str, Any]], blockers: list[str]) -> list[str]:
    if blockers:
        return [
            "주소, 보증금, 전용면적, 건물 동·호수 등 필수 정보를 먼저 보완하세요.",
            f"{_link('registry')}에서 등기부등본 최신본을 발급하고 주소·동호수·소유자·근저당·압류·신탁 여부를 다시 확인하세요.",
            f"{_link('building')} 또는 {_link('eais')}에서 건축물대장 최신본을 확인하세요.",
        ]
    actions = [
        f"계약 직전 {_link('registry')}에서 등기부등본 최신본을 다시 발급해 근저당·압류·가압류·신탁·전세권·임차권등기·가등기·경매·가처분 여부를 확인하세요.",
        f"{_link('building')} 또는 {_link('eais')}에서 건축물대장을 확인하고 주소, 동호수, 용도, 면적, 위반건축물 표시 여부를 대조하세요.",
        f"{_link('hug')}에서 보증 가능성, 보증한도, 제출서류를 확인하세요.",
    ]
    keys = {signal["key"] for signal in signals}
    if "mortgage" in keys or "mortgage_burden" in keys:
        _append_unique(actions, "채권최고액과 보증금을 합산해 추정 매매가 대비 비율을 확인하고, 잔금 전 근저당 말소 조건과 미이행 시 계약 해제·손해배상 특약을 계약서에 적으세요.")
    if "trust" in keys:
        _append_unique(actions, "신탁등기가 있으면 수탁자 동의서, 신탁원부, 임대 권한을 문서로 확인하기 전까지 계약 진행을 보류하세요.")
    if "seizure" in keys or "provisional_seizure" in keys:
        _append_unique(actions, "압류·가압류가 있으면 말소 가능 여부, 말소 예정일, 말소 확인 서류를 공인중개사·법률 전문가·관할 기관과 확인하세요.")
    if "jeonse_right" in keys:
        _append_unique(actions, "전세권등기가 있으면 전세권자, 설정 범위, 순위, 존속기간, 말소 조건을 등기부 원문과 계약서 특약으로 확인하세요.")
    if "leasehold_registration" in keys:
        _append_unique(actions, "임차권등기가 있으면 이전 임차인의 보증금 반환 분쟁 가능성이 있으므로 말소 여부와 보증금 반환 이력을 확인하기 전까지 계약을 보류하세요.")
    if "registry_warning" in keys:
        _append_unique(actions, "가등기·경매·가처분·소유권이전청구권 등 주의 권리관계가 있으면 임차권 확보에 영향을 줄 수 있으므로 법률 전문가 검토 전 계약을 진행하지 마세요.")
    if "ownership_transfer" in keys:
        _append_unique(actions, "최근 소유권 이전·보존 단서가 있으면 현재 소유자 신분, 매매 직후 전세계약 여부, 위임장·인감증명서 등 임대 권한 자료를 대조하세요.")
    if "senior_deposit" in keys:
        _append_unique(actions, "다가구는 선순위 임차보증금 총액과 확정일자 현황을 임대인·중개사에게 서면으로 확인하세요.")
    if "registry_unchecked" in keys:
        _append_unique(actions, f"{_link('registry')}에서 등기부등본 최신본을 발급받으세요.")
    if "building_unchecked" in keys or "violation" in keys or "non_residential" in keys:
        _append_unique(actions, f"{_link('building')} 또는 {_link('eais')}에서 건축물대장 최신본을 발급해 용도·면적·위반건축물 표시를 확인하세요.")
    if "violation" in keys:
        _append_unique(actions, "위반건축물로 표시되면 보증보험·대출·전입 가능성에 제한이 생길 수 있으므로 위반 내용과 시정 가능 여부를 확인하세요.")
    if "non_residential" in keys:
        _append_unique(actions, "주용도가 비주택이면 실제 주거 사용 가능성, 보증보험 가능성, 전입신고 가능성을 별도로 확인하세요.")
    _append_unique(actions, f"입주 직후 {_link('move_in')}를 진행하고, 계약서에는 {_link('fixed_date')} 또는 주민센터에서 확정일자를 받으세요.")
    _append_unique(actions, f"전세사기 예방 체크리스트는 {_link('safehome')}에서 한 번 더 확인하세요.")
    return actions
