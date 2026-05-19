from __future__ import annotations

from typing import Any


def grade_risk(score: int, snapshot: dict[str, Any], blockers: list[str]) -> dict[str, str]:
    if blockers:
        return {"grade": "검토불가", "message": "현재 정보만으로는 판단 범위가 제한됩니다."}
    if snapshot.get("trust_flag"):
        return {"grade": "고위험", "message": "신탁등기가 확인되어 전문가 확인이 필요합니다."}
    if snapshot.get("seizure_flag") or snapshot.get("provisional_seizure_flag"):
        return {"grade": "위험" if score < 75 else "고위험", "message": "압류 또는 가압류 신호가 있습니다."}
    if score >= 75:
        return {"grade": "고위험", "message": "여러 위험 신호가 겹쳐 전문가 상담 또는 추가 확인이 필요합니다."}
    if score >= 50:
        return {"grade": "위험", "message": "보증금 반환 위험이 커질 수 있어 계약 전 재검토가 필요합니다."}
    if score >= 25:
        return {"grade": "주의", "message": "일부 위험 신호가 있어 추가 확인이 필요합니다."}
    return {"grade": "확인 양호", "message": "현재 확인된 정보 기준 큰 위험 신호는 적습니다."}
