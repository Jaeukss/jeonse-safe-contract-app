from __future__ import annotations

from typing import Literal


DocumentType = Literal["registry", "building", "explanation", "unknown"]

KEYWORDS = {
    "registry": ["등기사항전부증명서", "갑구", "을구", "근저당권", "압류", "신탁", "채권최고액"],
    "building": ["건축물대장", "주용도", "위반건축물", "사용승인일", "전유부분"],
    "explanation": ["중개대상물", "확인·설명서", "확인설명서", "권리관계", "공인중개사"],
}


def classify_document(text: str) -> DocumentType:
    compact = (text or "").replace(" ", "")
    scores = {
        doc_type: sum(1 for keyword in keywords if keyword.replace(" ", "") in compact)
        for doc_type, keywords in KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"  # type: ignore[return-value]
