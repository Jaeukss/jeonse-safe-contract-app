from __future__ import annotations

from typing import Any


def render_conflict_view(st: Any, conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    if not conflicts:
        return {}
    st.subheader("4. 충돌 확인")
    st.warning("OCR/체크박스/사용자 입력 사이에 다른 값이 발견되었습니다. 진단에 사용할 값을 선택하세요.")
    resolutions: dict[str, Any] = {}
    for conflict in conflicts:
        field = conflict["field"]
        left = conflict["left"]
        right = conflict["right"]
        recommended = conflict["recommended"]
        st.markdown(f"**항목: {field}**")
        st.caption(f"{left['source']}: {left['value']} / {right['source']}: {right['value']}")
        options = [recommended["value"], left["value"], right["value"], None]
        labels = [str(value) if value is not None else "모름" for value in options]
        choice = st.radio(
            "진단에 사용할 값",
            options=list(range(len(options))),
            format_func=lambda index, labels=labels: labels[index],
            key=f"resolve_{field}",
            horizontal=True,
        )
        resolutions[field] = options[choice]
    return resolutions
