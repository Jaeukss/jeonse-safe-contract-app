from __future__ import annotations

from typing import Any


def add_signal(signals: list[dict[str, Any]], points: int, key: str, title: str, detail: str) -> None:
    signals.append({"points": points, "key": key, "title": title, "detail": detail})


def calculate_risk_score(snapshot: dict[str, Any], market: dict[str, Any]) -> tuple[int, list[dict[str, Any]], list[str]]:
    score = int(market.get("market_risk_score", 0))
    signals: list[dict[str, Any]] = []
    if market["jeonse_ratio"] >= 90:
        add_signal(signals, 30, "jeonse_ratio", "전세가율 90% 이상", f"전세가율이 {market['jeonse_ratio']}%입니다.")
    elif market["jeonse_ratio"] >= 80:
        add_signal(signals, 15, "jeonse_ratio", "전세가율 80% 이상", f"전세가율이 {market['jeonse_ratio']}%입니다.")
    if market["rent_gap_rate"] >= 130:
        add_signal(signals, 30, "rent_gap_rate", "시세괴리율 130% 이상", f"시세괴리율이 {market['rent_gap_rate']}%입니다.")
    elif market["rent_gap_rate"] >= 115:
        add_signal(signals, 20, "rent_gap_rate", "시세괴리율 115% 이상", f"시세괴리율이 {market['rent_gap_rate']}%입니다.")
    if market["similar_transaction_count"] == 0:
        add_signal(signals, 20, "market_insufficient", "유사 거래 없음", "시세 판단이 제한됩니다.")
    elif market["similar_transaction_count"] <= 2:
        add_signal(signals, 10, "market_low_count", "유사 거래 부족", "시세 신뢰도가 낮습니다.")

    if snapshot.get("mortgage_flag"):
        score += 20
        add_signal(signals, 20, "mortgage", "근저당권 확인", "채권최고액과 보증금을 합산해 매매가 대비 수준을 확인해야 합니다.")
    if snapshot.get("mortgage_amount") and snapshot.get("deposit") and market.get("predicted_sale_price"):
        burden_ratio = (int(snapshot["mortgage_amount"]) + int(snapshot["deposit"])) / int(market["predicted_sale_price"]) * 100
        if burden_ratio >= 90:
            score += 30
            add_signal(signals, 30, "mortgage_burden", "채권최고액+보증금 90% 이상", f"합산 부담률이 {burden_ratio:.1f}%입니다.")
        elif burden_ratio >= 80:
            score += 30
            add_signal(signals, 30, "mortgage_burden", "채권최고액+보증금 80% 이상", f"합산 부담률이 {burden_ratio:.1f}%입니다.")
    if snapshot.get("seizure_flag"):
        score += 40
        add_signal(signals, 40, "seizure", "압류 확인", "소유자의 채무 문제로 권리관계가 복잡할 수 있습니다.")
    if snapshot.get("provisional_seizure_flag"):
        score += 40
        add_signal(signals, 40, "provisional_seizure", "가압류 확인", "권리관계 확인이 필요합니다.")
    if snapshot.get("trust_flag"):
        score += 50
        add_signal(signals, 50, "trust", "신탁등기 확인", "임대 권한과 수탁자 동의 여부를 확인해야 합니다.")
    if snapshot.get("leasehold_registration_flag"):
        score += 30
        add_signal(signals, 30, "leasehold_registration", "임차권등기 확인", "이전 임차인의 보증금 문제가 있었을 수 있습니다.")
    if snapshot.get("ownership_transfer_recent_flag"):
        score += 10
        add_signal(signals, 10, "ownership_transfer", "최근 소유권 이전", "소유권 변동 사유 확인이 필요합니다.")
    if snapshot.get("violation_flag"):
        score += 25
        add_signal(signals, 25, "violation", "위반건축물 확인", "보증보험 또는 주거 안정성에 영향을 줄 수 있습니다.")
    if snapshot.get("non_residential_usage_flag"):
        score += 25
        add_signal(signals, 25, "non_residential", "주용도 비주택", "주거용도 적합성을 확인해야 합니다.")
    if not snapshot.get("registry_checked"):
        score += 20
        add_signal(signals, 20, "registry_unchecked", "등기부등본 미확인", "근저당, 압류, 신탁 여부를 판단할 수 없습니다.")
    if not snapshot.get("building_register_checked") and not snapshot.get("public_building_matched"):
        score += 15
        add_signal(signals, 15, "building_unchecked", "건축물대장 미확인", "위반건축물 및 용도 확인이 제한됩니다.")
    if not snapshot.get("broker_explanation_checked"):
        score += 10
        add_signal(signals, 10, "explanation_unchecked", "중개대상물 확인설명서 미확인", "권리관계 설명 여부가 불명확합니다.")
    if snapshot.get("housing_type") == "다가구" and not snapshot.get("senior_deposit_checked"):
        score += 30
        add_signal(signals, 30, "senior_deposit", "다가구 선순위 보증금 미확인", "선순위 임차보증금 총액 확인이 필요합니다.")

    blockers = []
    if not snapshot.get("address") or not snapshot.get("deposit") or not snapshot.get("area_m2"):
        blockers.append("필수 입력 정보 부족")
    return min(score, 100), sorted(signals, key=lambda item: item["points"], reverse=True), blockers
