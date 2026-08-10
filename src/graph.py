from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, RetryPolicy

from .chain import build_analysis_chain
from .models import ReviewAnalysis
from .rag import suggest_solution
from .tools import escalate_ticket


class State(TypedDict):
    review_id: str
    review: str
    analysis: ReviewAnalysis | None
    draft_response: dict | None   # {"resolution": str, "sources": list[str]} from suggest_solution
    status: str                    # 'new' | 'drafted' | 'escalated' | 'approved' | 'rejected' | 'sent'
    approved: bool | None


_analysis_chain = None


def _get_analysis_chain():
    """Lazy-build once and reuse - mirrors the pattern already used for the cross-encoder in rag.py."""
    global _analysis_chain
    if _analysis_chain is None:
        _analysis_chain = build_analysis_chain()
    return _analysis_chain


def classify_node(state: State) -> dict:
    """Run Day 2's chain, set analysis."""
    chain = _get_analysis_chain()
    analysis = chain.invoke({"review": state["review"]})
    return {"analysis": analysis, "status": "analyzed"}


def route_by_severity(state: State) -> str:
    """Conditional edge: severity >= 4 -> 'escalate', else 'retrieve'."""
    if state["analysis"].severity >= 4:
        return "escalate"
    return "retrieve"


def retrieve_node(state: State) -> dict:
    """Run Day 3's RAG, set draft_response. Routine issues - no human approval needed after this."""
    result = suggest_solution(state["analysis"])
    return {"draft_response": result, "status": "drafted"}


def escalate_node(state: State) -> dict:
    """Call Day 4's escalate_ticket tool, and also draft a grounded resolution so the human
    reviewing at approval_node has something concrete to approve or reject."""
    escalate_ticket(review_id=state["review_id"], reason=state["analysis"].summary)
    result = suggest_solution(state["analysis"])
    return {"draft_response": result, "status": "escalated"}


def approval_node(state: State) -> dict:
    """interrupt() here to PAUSE for human approval before sending a response to an angry
    customer. Resume applies the human's decision via Command(resume=...)."""
    decision = interrupt(
        {
            "review": state["review"],
            "draft_response": state["draft_response"],
            "message": "Approve sending this response to the customer?",
        }
    )
    approved = bool(decision)
    return {"approved": approved, "status": "approved" if approved else "rejected"}


def send_node(state: State) -> dict:
    """Terminal node - 'sends' the response (printed, since there's no real customer messaging
    infra) unless the human rejected it at approval_node."""
    if state["status"] == "rejected":
        return {"status": "not_sent"}
    print(f"[SENT to customer] {state['draft_response']['resolution']}")
    return {"status": "sent"}


def build_graph(checkpointer):
    """Wire nodes + edges + the conditional edge + the given checkpointer (so it's durable).
    Retry policy on classify/retrieve/escalate - the nodes that call external APIs/tools -
    directly answers Day 5's break-test 2 finding (create_agent crashed on a tool error instead
    of retrying)."""
    retry = RetryPolicy(max_attempts=3)

    graph = StateGraph(State)
    graph.add_node("classify", classify_node, retry_policy=retry)
    graph.add_node("retrieve", retrieve_node, retry_policy=retry)
    graph.add_node("escalate", escalate_node, retry_policy=retry)
    graph.add_node("approval", approval_node)
    graph.add_node("send", send_node)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify", route_by_severity, {"escalate": "escalate", "retrieve": "retrieve"}
    )
    graph.add_edge("retrieve", "send")
    graph.add_edge("escalate", "approval")
    graph.add_edge("approval", "send")
    graph.add_edge("send", END)

    return graph.compile(checkpointer=checkpointer)
