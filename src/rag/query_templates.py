from __future__ import annotations


RISK_EXPLANATIONS = {
    "jeonse_ratio": "보증금이 집값에 가까울수록 경매 등 상황에서 회수 여지가 줄어들 수 있습니다.",
    "rent_gap_rate": "주변 전세 시세보다 보증금이 높으면 과도한 보증금일 가능성이 있습니다.",
    "mortgage": "근저당권은 집에 선순위 담보가 있을 수 있음을 의미하므로 채권최고액 확인이 필요합니다.",
    "seizure": "압류는 소유자의 채무 문제와 연결될 수 있어 계약 전 전문가 확인이 필요합니다.",
    "provisional_seizure": "가압류는 향후 권리관계 변동 가능성이 있어 추가 확인이 필요합니다.",
    "trust": "신탁등기는 임대 권한과 수탁자 동의 여부를 반드시 확인해야 합니다.",
    "violation": "위반건축물은 보증보험, 대출, 주거 안정성에 영향을 줄 수 있습니다.",
    "registry_unchecked": "등기부등본을 확인하지 않으면 근저당, 압류, 신탁 여부를 판단할 수 없습니다.",
    "building_unchecked": "건축물대장을 확인하지 않으면 위반건축물 및 용도를 판단하기 어렵습니다.",
    "senior_deposit": "다가구주택은 내 보증금보다 먼저 보호받는 선순위 보증금이 있을 수 있습니다.",
}


def explanation_for(key: str) -> str:
    return RISK_EXPLANATIONS.get(key, "계약 전 원문 문서와 최신 공적 장부 확인이 필요합니다.")
