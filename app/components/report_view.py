from __future__ import annotations

from typing import Any

from src.risk.document_signals import build_document_signal_cards
from src.report.generate_report import official_check_links


def render_report_view(st: Any, result: dict[str, Any]) -> None:
    grade = result["grade"]
    market = result["market"]
    snapshot = result["snapshot"]
    st.subheader("최종 리포트")
    st.metric("전세계약 위험등급", grade["grade"], grade["message"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("위험 점수", f"{result['score']}점")
    c2.metric("전세가율", f"{market['jeonse_ratio']}%")
    c3.metric("시세괴리율", f"{market['rent_gap_rate']}%")
    c4.metric("시세 신뢰도", market["market_confidence"])

    st.markdown("### 문서 신호")
    cards = build_document_signal_cards(snapshot)
    for row_start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, card in zip(cols, cards[row_start : row_start + 3]):
            col.info(f"{card['label']}: {card['status']}")

    st.markdown("### 핵심 위험 신호")
    if result["signals"]:
        for signal in result["signals"]:
            st.markdown(f"- **{signal['title']}**: {signal['detail']} (+{signal['points']}점)")
    else:
        st.success("현재 확인된 정보 기준 큰 위험 신호는 적습니다.")

    st.markdown("### 다음 행동")
    for action in result["actions"]:
        st.markdown(f"- {action}")

    st.markdown("### 공식 확인 링크")
    for item in official_check_links():
        st.markdown(f"- [{item['title']}]({item['url']})")

    st.download_button(
        "Markdown 리포트 다운로드",
        data=result["report_markdown"].encode("utf-8"),
        file_name="gwanak-jeonse-risk-report.md",
        mime="text/markdown",
        use_container_width=True,
    )
