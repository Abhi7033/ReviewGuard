# ReviewGuard

An agent that takes a customer review → judges sentiment → analyzes it → suggests a **grounded**
resolution from a real knowledge base → escalates and pauses for human approval when the customer
is angry, surviving a process restart mid-approval.

Built day-by-day as a learn-by-building project (see `reviewguard-build-plan.md`) — every backend
function was hand-written and reviewed line by line, not generated. One commit per day; the git
history is the actual portfolio. Full list of what broke and why is in [`FAILURES.md`](FAILURES.md).

## Architecture

```mermaid
flowchart TD
    START([review text]) --> classify[classify_node<br/>Day 2 LCEL chain]
    classify -->|severity < 4| retrieve[retrieve_node<br/>Day 3 grounded RAG]
    classify -->|severity >= 4| escalate[escalate_node<br/>Day 4 escalate_ticket + Day 3 RAG]
    retrieve --> send[send_node]
    escalate --> approval[approval_node<br/>interrupt - pauses for a human]
    approval -->|approved| send
    approval -->|rejected| send
    send --> END([sent / not_sent])
```

Routine reviews (severity < 4) get a grounded resolution drafted and sent automatically. Severe
or angry reviews (severity ≥ 4) get a real support ticket, a drafted resolution, and then the
graph **genuinely pauses** at `approval_node` until a human approves or rejects it — confirmed by
killing the process mid-pause and resuming it in a separate process using only the persisted
SQLite checkpoint (see Day 6 in `FAILURES.md`).

## Stack

- **Model**: Google Gemini (`gemini-3.5-flash`) via the AI Studio free tier — the original plan
  targeted Anthropic, but was migrated early (see Day 1 in `FAILURES.md`); old Anthropic call
  sites are kept as comments rather than deleted, for reference.
- **RAG**: Chroma (persistent, local) + BM25 (`rank_bm25`) fused with Reciprocal Rank Fusion,
  reranked with a cross-encoder (`sentence-transformers`).
- **Orchestration**: hand-written tool loop (Day 4) → `langchain.agents.create_agent` (Day 5) →
  explicit `langgraph.graph.StateGraph` (Day 6) — each stage built to feel the layer underneath
  the next one before trusting it.
- **Tracing**: LangSmith, verified by querying its API directly for real runs, not just assuming
  a non-error meant tracing worked.
- **Eval**: a scored end-to-end test set (`eval/e2e_eval.py`) that exits 1 on regression — proven
  against an actual injected quality regression, not just written and trusted.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GOOGLE_API_KEY (aistudio.google.com/apikey) and LANGSMITH_API_KEY
```

Build the retrieval index once (or whenever `data/kb/` changes):

```bash
python3 -m src.ingest
```

Run the eval / CI gate:

```bash
python3 -m eval.e2e_eval   # exits 1 if score drops below 0.80
python3 -m eval.retrieval_eval   # retrieval hit-rate, naive vs hybrid
```

## Retrieval: measured, not assumed

The single most differentiating piece of this project, per the plan's own framing — retrieval
quality was actually measured before and after an upgrade, not just built and hoped for:

| | hit_rate@1 |
|---|---|
| Naive vector search only | 0.83 (15/18) |
| + BM25 + Reciprocal Rank Fusion + cross-encoder rerank | **0.94** (17/18) |

The one query that still misses in both versions ("I want to return this, it doesn't fit" →
matches `damaged_item_guide.md` instead of `return_exchange_policy.txt`) isn't a retrieval
algorithm problem — the two docs are genuinely close in *meaning*, and the real fix is clearer
knowledge base content, not a better algorithm. Full breakdown in `FAILURES.md`.

## What actually broke (highlights — full log in FAILURES.md)

- **Bare Gemini model names can silently resolve to Vertex AI** (a different Google product,
  incompatible credentials) via `init_chat_model` unless the `google_genai:` prefix is explicit.
- **Free-tier quota is scoped to the Google Cloud project, not the API key** — a fresh key from
  the same account doesn't reset an exhausted daily cap.
- **`create_agent` doesn't recover from tool errors or step-limit overruns by default** — both
  crash the whole run; Day 6's LangGraph `retry_policy` is the direct fix.
- **LangGraph's checkpoint serialization won't indefinitely trust arbitrary Pydantic objects** in
  `State` — a real forward-compatibility warning caught by actually reading the output, not just
  checking for a non-zero exit code.
- **Always verify a fast-moving SDK against what's actually installed**, not training-data memory
  — this bit twice (MCP's `FastMCP` → `MCPServer` rename, LangGraph SQLite checkpointer API).

## Progress

- [x] Day 1 — raw sentiment classifier (no framework)
- [x] Day 2 — LCEL chain, swappable provider
- [x] Day 3 — RAG for grounded solutions, naive → measured → hybrid
- [x] Day 4 — tools: hand-written loop + MCP
- [x] Day 5 — high-level agent (`create_agent`), deliberately broken
- [x] Day 6 — LangGraph state machine: severity routing, human-approval interrupt, durable restart
- [x] Day 7 — scored eval + CI gate, tracing confirmed, shipped
