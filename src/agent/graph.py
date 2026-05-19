from __future__ import annotations

from .nodes import create_snapshot_node, evidence_node, predict_price_node, report_node, risk_node
from .state import AgentState


def run_agent_workflow(state: AgentState) -> AgentState:
    for node in (create_snapshot_node, predict_price_node, risk_node, evidence_node, report_node):
        state = node(state)
    return state


def build_langgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except Exception:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("create_snapshot", create_snapshot_node)
    graph.add_node("predict_price", predict_price_node)
    graph.add_node("calculate_risk", risk_node)
    graph.add_node("retrieve_evidence", evidence_node)
    graph.add_node("generate_report", report_node)
    graph.add_edge(START, "create_snapshot")
    graph.add_edge("create_snapshot", "predict_price")
    graph.add_edge("predict_price", "calculate_risk")
    graph.add_edge("calculate_risk", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()
