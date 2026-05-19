from __future__ import annotations

from typing import Any

from .address import NormalizedContract
from .document_ai import DocumentSignals
from .models import PricePrediction


def generate_risk_features(
    contract: NormalizedContract,
    docs: DocumentSignals,
    prediction: PricePrediction,
    market: dict[str, Any],
    checks: dict[str, bool],
) -> dict[str, Any]:
    sale = max(prediction.predicted_sale_price, 1)
    rent = max(prediction.predicted_rent_price, 1)
    return {
        "predicted_rent_price": prediction.predicted_rent_price,
        "predicted_sale_price": prediction.predicted_sale_price,
        "jeonse_ratio": contract.deposit_won / sale * 100,
        "rent_gap_rate": contract.deposit_won / rent * 100,
        "similar_transaction_count": market["similar_transaction_count"],
        "mortgage_flag": docs.mortgage_flag,
        "mortgage_amount": docs.mortgage_amount,
        "seizure_flag": docs.seizure_flag,
        "provisional_seizure_flag": docs.provisional_seizure_flag,
        "trust_flag": docs.trust_flag,
        "violation_flag": docs.violation_flag,
        "registry_checked": checks["registry_checked"],
        "building_checked": checks["building_checked"],
        "explanation_checked": checks["explanation_checked"],
        "senior_deposit_unknown": checks["senior_deposit_unknown"],
        "model_note": prediction.model_note,
    }


def score_risk(features: dict[str, Any], housing_type: str) -> tuple[int, list[dict[str, Any]]]:
    score = 0
    signals: list[dict[str, Any]] = []

    def add(points: int, level: str, title: str, detail: str, key: str) -> None:
        nonlocal score
        score += points
        signals.append({"points": points, "level": level, "title": title, "detail": detail, "key": key})

    if features["jeonse_ratio"] >= 90:
        add(35, "위험", "전세가율 90% 이상", f"보증금이 추정 매매가의 {features['jeonse_ratio']:.1f}%입니다.", "jeonse_ratio")
    elif features["jeonse_ratio"] >= 80:
        add(22, "주의", "전세가율 80% 이상", f"보증금이 추정 매매가의 {features['jeonse_ratio']:.1f}%입니다.", "jeonse_ratio")
    if features["rent_gap_rate"] >= 115:
        add(18, "주의", "주변 시세보다 높은 보증금", f"예측 적정 전세가 대비 {features['rent_gap_rate']:.1f}% 수준입니다.", "rent_gap")
    if features["similar_transaction_count"] < 3:
        add(12, "확인", "유사 거래 부족", "같은 법정동·유형·면적의 비교 거래가 부족해 시세 신뢰도가 낮습니다.", "rent_gap")
    if features["mortgage_flag"]:
        add(20, "주의", "근저당권 확인", "등기부상 선순위 채권 가능성이 있어 채권최고액과 말소 조건 확인이 필요합니다.", "mortgage")
    if features["seizure_flag"] or features["provisional_seizure_flag"]:
        add(38, "위험", "압류·가압류 확인", "소유자의 채무 문제로 처분 제한이 있을 수 있어 계약 보류와 전문가 검토가 필요합니다.", "seizure")
    if features["trust_flag"]:
        add(45, "고위험", "신탁등기 확인", "임대 권한자가 등기상 소유자와 다를 수 있어 신탁원부와 수탁자 동의 확인이 필요합니다.", "trust")
    if features["violation_flag"]:
        add(18, "주의", "위반건축물 확인", "보증보험, 대출, 주택 용도 판단에 영향을 줄 수 있습니다.", "violation")
    if housing_type == "다가구" or features["senior_deposit_unknown"]:
        add(12, "확인", "다가구 선순위 보증금 확인", "같은 건물의 다른 임차인 보증금 총액이 반환 순위에 영향을 줄 수 있습니다.", "multifamily")
    if not features["registry_checked"] or not features["building_checked"]:
        add(10, "확인", "필수 문서 미확인", "계약 전과 잔금 전 등기부등본과 건축물대장을 다시 발급해 확인해야 합니다.", "unchecked")

    return min(score, 100), sorted(signals, key=lambda item: item["points"], reverse=True)


def grade(score: int, features: dict[str, Any], missing_fields: list[str]) -> str:
    if missing_fields:
        return "검토불가"
    if features["trust_flag"] or score >= 85:
        return "고위험"
    if score >= 60:
        return "위험"
    if score >= 28:
        return "주의"
    return "안전"
