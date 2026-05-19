from __future__ import annotations

from typing import Any


def route_diagnosis(features: dict[str, Any], signals: list[dict[str, Any]]) -> list[str]:
    routes = ["load_input", "normalize", "compare_market", "extract_document_signals"]
    keys = {signal["key"] for signal in signals}
    if "trust" in keys:
        routes.append("trust_review_required")
    if "seizure" in keys:
        routes.append("seizure_or_provisional_seizure_review")
    if "multifamily" in keys:
        routes.append("senior_deposit_check")
    if features["similar_transaction_count"] < 3:
        routes.append("low_confidence_market_search")
    routes.extend(["retrieve_rag_evidence", "generate_report"])
    return routes


LANGGRAPH_DESIGN = {
    "nodes": [
        "load_input",
        "normalize",
        "compare_market",
        "predict_prices",
        "extract_document_signals",
        "generate_features",
        "conditional_review",
        "retrieve_rag_evidence",
        "generate_report",
    ],
    "conditional_edges": {
        "trust_flag": "trust_review_required",
        "seizure_flag": "seizure_or_provisional_seizure_review",
        "housing_type == 다가구": "senior_deposit_check",
        "similar_transaction_count < 3": "low_confidence_market_search",
    },
}
