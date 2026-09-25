from functools import partial

from langgraph.graph import StateGraph, END

from app.orchestrator.state import AuditGraphState, StepStatus
from app.orchestrator.nodes.run_residency import run_residency
from app.orchestrator.nodes.run_credit import run_credits
from app.orchestrator.nodes.run_explanation import run_explanation
from app.orchestrator.nodes.run_persistence import run_persistence


def _route_after_residency(state: AuditGraphState) -> str:
    if state.residency_step_status == StepStatus.FAILED:
        return END
    return "run_credits"


def _route_after_credits(state: AuditGraphState) -> str:
    if state.credit_evaluation_step_status == StepStatus.FAILED:
        return END
    return "run_explanation"


def build_audit_graph(service_client, llm=None):
    """
    service_client is the only client dependency now — the fictional
    db_client from an earlier draft has been removed; every fetch goes
    through service_client directly, matching how the rest of this
    project already talks to Supabase.
    """
    graph_builder = StateGraph(AuditGraphState)

    graph_builder.add_node(
        "run_residency",
        partial(run_residency, service_client=service_client),
    )
    graph_builder.add_node(
        "run_credits",
        partial(run_credits, service_client=service_client),
    )
    graph_builder.add_node(
        "run_explanation",
        partial(run_explanation, llm=llm),
    )
    graph_builder.add_node(
        "run_persistence",
        partial(run_persistence, service_client=service_client),
    )

    graph_builder.set_entry_point("run_residency")

    graph_builder.add_conditional_edges(
        "run_residency",
        _route_after_residency,
        {"run_credits": "run_credits", END: END},
    )
    graph_builder.add_conditional_edges(
        "run_credits",
        _route_after_credits,
        {"run_explanation": "run_explanation", END: END},
    )
    graph_builder.add_edge("run_explanation", "run_persistence")
    graph_builder.add_edge("run_persistence", END)

    return graph_builder.compile()