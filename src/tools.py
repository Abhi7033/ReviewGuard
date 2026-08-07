import json
from datetime import datetime, timezone
from pathlib import Path

from .rag import retrieve_hybrid

ORDERS_PATH = Path("data/orders.json")
TICKETS_PATH = Path("data/tickets.jsonl")

def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for guidance relevant to a customer's issue."""
    results = retrieve_hybrid(query, k_candidates=20, k_final=3)
    if not results:
        return "No relevant knowledge base articles found."
    return "\n\n".join(f"[{r['source']}]\n{r['text']}" for r in results)


def lookup_order(order_id: str) -> str:
    """Read data/orders.json, return the record or 'not found'."""
    orders = json.loads(ORDERS_PATH.read_text())
    for order in orders:
        if order["order_id"] == order_id:
            return json.dumps(order)
    return f"Order {order_id} not found."


def escalate_ticket(review_id: str, reason: str) -> str:
    """Append a ticket to data/tickets.jsonl, return confirmation."""
    ticket = {
        "review_id": review_id,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with TICKETS_PATH.open("a") as f:
        f.write(json.dumps(ticket) + "\n")
    return f"Ticket escalated for review {review_id}."


TOOL_SCHEMAS = [
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the customer support knowledge base for policy and resolution guidance "
            "relevant to a customer's issue. Use this before drafting any resolution to a "
            "customer complaint, refund request, shipping issue, damaged item, billing error, "
            "etc. Input should be a short description of the customer's issue."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The customer's issue, in a few words, e.g. 'damaged item refund'.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "lookup_order",
        "description": (
            "Look up the status and shipping info of a specific order by its order ID. Use this "
            "when the customer references a specific order ID (looks like 'ORD-1001') and you "
            "need to confirm its current status before responding."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID, e.g. 'ORD-1001'."}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "escalate_ticket",
        "description": (
            "Escalate a review to a human support agent when the issue cannot be resolved "
            "automatically - e.g. the customer is very angry, the issue isn't covered by the "
            "knowledge base, or they explicitly ask for a human. Use only as a last resort, "
            "not for routine issues the knowledge base already covers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "review_id": {
                    "type": "string",
                    "description": "An identifier for the review being escalated.",
                },
                "reason": {"type": "string", "description": "Why this review is being escalated."},
            },
            "required": ["review_id", "reason"],
        },
    },
]


TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "lookup_order": lookup_order,
    "escalate_ticket": escalate_ticket,
}
