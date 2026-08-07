from dotenv import load_dotenv
from langchain.agents import create_agent

from .tools import escalate_ticket, lookup_order, search_knowledge_base

load_dotenv()

SYSTEM_PROMPT = """You are a customer support triage agent for ReviewGuard. Given a customer
review, resolve it using the tools available to you:

- search_knowledge_base: find the relevant policy/resolution guidance before drafting any answer.
- lookup_order: check a specific order's status if the customer mentions an order ID.
- escalate_ticket: escalate to a human only if you cannot resolve the issue yourself - not for
  routine issues the knowledge base already covers.

Ground your final resolution in what the knowledge base actually says - do not invent policy.
"""


def build_agent():
    """create_agent(model, tools=[...]) with our 3 tools passed as plain callables - create_agent
    infers each tool's schema from its type hints and docstring, same pattern as MCP's @mcp.tool().
    Returns a CompiledStateGraph (create_agent is a pre-built LangGraph graph, not a separate
    paradigm from Day 6)."""
    return create_agent(
        model="google_genai:gemini-3.5-flash",
        tools=[search_knowledge_base, lookup_order, escalate_ticket],
        system_prompt=SYSTEM_PROMPT,
    )
