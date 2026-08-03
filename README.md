# ReviewGuard

An agent that takes a customer review → judges sentiment → analyzes it → suggests a grounded
resolution from a knowledge base → escalates or pauses for human approval when the customer is angry.

Built day-by-day as a learning project (see `reviewguard-build-plan.md`). One commit per day.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

## Progress

- [ ] Day 1 — raw sentiment classifier
- [ ] Day 2 — LCEL chain
- [ ] Day 3 — RAG for grounded solutions
- [ ] Day 4 — tools (hand-written loop + MCP)
- [ ] Day 5 — high-level agent
- [ ] Day 6 — LangGraph state machine
- [ ] Day 7 — eval, observability, ship
