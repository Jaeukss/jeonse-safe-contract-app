from __future__ import annotations

from src.input_layer.snapshot import create_snapshot
from src.modeling.predict_price import predict_prices
from src.rag.retrieve_evidence import retrieve_evidence
from src.report.generate_report import generate_markdown_report, recommended_actions
from src.risk.market_indicators import calculate_market_indicators
from src.risk.risk_grade import grade_risk
from src.risk.risk_rules import calculate_risk_score

from .state import AgentState


def create_snapshot_node(state: AgentState) -> AgentState:
    snapshot = create_snapshot(state["session_id"], state["records"], state.get("resolutions"))
    state["snapshot"] = snapshot.confirmed_data
    state["conflicts"] = snapshot.conflicts
    return state


def predict_price_node(state: AgentState) -> AgentState:
    prediction = predict_prices(state["snapshot"])
    state["prediction"] = prediction
    state["market"] = {**prediction, **calculate_market_indicators(state["snapshot"], prediction)}
    return state


def risk_node(state: AgentState) -> AgentState:
    score, signals, blockers = calculate_risk_score(state["snapshot"], state["market"])
    state["score"] = score
    state["signals"] = signals
    state["blockers"] = blockers
    state["grade"] = grade_risk(score, state["snapshot"], blockers)
    return state


def evidence_node(state: AgentState) -> AgentState:
    state["evidence"] = retrieve_evidence([signal["key"] for signal in state.get("signals", [])])
    state["actions"] = recommended_actions(state.get("signals", []), state.get("blockers", []))
    return state


def report_node(state: AgentState) -> AgentState:
    state["report_markdown"] = generate_markdown_report(state)
    return state
