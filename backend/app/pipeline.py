from __future__ import annotations

from typing import Any

from .address import normalize_contract
from .agent import route_diagnosis
from .document_ai import extract_document_signals
from .market import market_summary
from .models import predict_prices
from .rag import retrieve_evidence
from .registry_search import retrieve_registry_matches
from .report import action_list, render_html_report
from .risk import generate_risk_features, grade, score_risk
from .schemas import ContractInput, DiagnosisResponse


def diagnose_contract(payload: ContractInput) -> DiagnosisResponse:
    contract = normalize_contract(payload)
    docs = extract_document_signals(payload.document_text)
    market = market_summary(contract)
    prediction = predict_prices(contract, market)
    checks = {
        "registry_checked": payload.registry_checked,
        "building_checked": payload.building_checked,
        "explanation_checked": payload.explanation_checked,
        "senior_deposit_unknown": payload.senior_deposit_unknown,
    }
    features = generate_risk_features(contract, docs, prediction, market, checks)
    score, signals = score_risk(features, contract.housing_type)
    result_grade = grade(score, features, contract.missing_fields)
    evidence = retrieve_evidence([signal["key"] for signal in signals])
    registry_matches = retrieve_registry_matches(
        address=contract.address,
        legal_dong_code=contract.legal_dong_code,
        housing_type=contract.housing_type,
    )
    routes = route_diagnosis(features, signals)
    actions = action_list(signals)
    confidence = confidence_label(features, contract.missing_fields)
    features["agent_routes"] = routes
    features["market_summary"] = market
    features["missing_fields"] = contract.missing_fields
    features["building_registry_matches"] = registry_matches

    return DiagnosisResponse(
        grade=result_grade,
        score=score,
        confidence=confidence,
        features=features,
        signals=signals,
        evidence=evidence,
        actions=actions,
        report_html=render_html_report(result_grade, score, signals, evidence),
    )


def confidence_label(features: dict[str, Any], missing_fields: list[str]) -> str:
    if missing_fields:
        return "낮음"
    score = 25
    score += min(features["similar_transaction_count"] * 7, 35)
    score += 15 if features["registry_checked"] else 0
    score += 15 if features["building_checked"] else 0
    score += 10 if features["explanation_checked"] else 0
    if score >= 75:
        return "높음"
    if score >= 50:
        return "보통"
    return "낮음"
