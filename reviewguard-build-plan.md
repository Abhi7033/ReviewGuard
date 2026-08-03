# ReviewGuard — 7-Day Learn-by-Building Guide

**What you're building:** an agent that takes a customer review → judges sentiment → analyzes it → suggests a *grounded* resolution from a real knowledge base → escalates or pauses for human approval when the customer is angry.

**The rule:** YOU write every function body. This guide gives you the structure, the signatures, the concept each piece teaches, and TODO hints. It never hands you the implementation. When truly stuck on a specific API, check the current docs (`docs.langchain.com`, `docs.anthropic.com`) — never copy a whole tutorial.

**One commit per day.** Same repo grows all week. By Day 7 the git history *is* your portfolio.

---

## Day 0 — Setup (30 min, do before Day 1)

```bash
uv init reviewguard && cd reviewguard
uv add anthropic openai pydantic python-dotenv httpx
# (later days add: langchain langgraph chromadb rank-bm25 sentence-transformers ragas)
```

Structure you'll grow into:
```
reviewguard/
  .env                  # ANTHROPIC_API_KEY=... (never commit this)
  data/
    reviews.csv         # ~30 customer reviews (make or download)
    kb/                 # 12-15 short resolution/policy/FAQ docs (messy on purpose)
    orders.json         # mock order records for the lookup tool
  src/
  eval/
  FAILURES.md           # your Day 5 failure log
  README.md
```

**Get your data (you make this, it's part of the learning):**
- `reviews.csv`: columns `id,text`. Hand-write ~30 reviews spanning happy / neutral / furious / ambiguous / multi-issue. Or grab a public dataset (Amazon/Yelp reviews) and trim to 30. Deliberately include messy ones.
- `data/kb/`: 12–15 short docs — a refund policy, a shipping-delay FAQ, a "damaged item" resolution guide, warranty terms, etc. Vary the formats (some markdown, some plain prose, some with headings). Messiness is the point — clean data teaches you nothing about retrieval.
- `orders.json`: ~10 fake orders `{"order_id": "...", "status": "...", "ship_date": "..."}`.

---

## Day 1 — Stage 0: Raw sentiment classifier (no framework)

**Concept:** the request/response shape, structured output, and graceful failure — with zero abstraction hiding it.

**`src/models.py`**
```python
from pydantic import BaseModel, Field
from typing import Literal

class SentimentResult(BaseModel):
    """The structured shape you'll force the model to return.
    TODO define fields:
      sentiment: Literal["positive","neutral","negative"]
      confidence: float   # Field(ge=0, le=1)
      key_issues: list[str]   # concrete problems the customer named
      summary: str
    """
    ...
```

**`src/classify_raw.py`**
```python
def build_prompt(review: str) -> str:
    """Return a prompt that (1) states the task, (2) shows the EXACT JSON shape
    matching SentimentResult, (3) says 'respond with ONLY valid JSON, no code fences'.
    TODO: write this. A vague prompt is the #1 cause of malformed output. This is 60% of the work.
    """
    ...

def estimate_cost(review: str) -> float:
    """Rough input-token count × price-per-token. TODO: count tokens, multiply, return dollars.
    Concept: you should be able to guess a call's cost before making it."""
    ...

def classify_sentiment(review: str, max_retries: int = 1) -> SentimentResult:
    """
    TODO implement, in order:
      1. Call the raw API (anthropic.messages.create) with build_prompt(review).
      2. Pull out the text content.
      3. SentimentResult.model_validate_json(text)  -> return on success.
      4. On ValidationError: append the error text to the prompt and retry, telling the model
         exactly what was wrong. THIS retry pattern reappears every day this week — internalize it.
    """
    ...

def stream_explanation(review: str) -> None:
    """Separate call that STREAMS a human-readable explanation token-by-token to the terminal.
    TODO: use the streaming API and print chunks as they arrive."""
    ...
```

**Done when:** any review → validated `SentimentResult`; it recovers when you feed it a deliberately broken response; you print an estimated cost; streaming works.

---

## Day 2 — Stage 1: LCEL chain (classify + extract, swappable provider)

**Concept:** compose `prompt | model | parser` into a reliable pipeline; recognize a chain is enough here (no agent needed yet).

**`src/chain.py`**
```python
# Richer schema than Day 1 — add to models.py:
class ReviewAnalysis(BaseModel):
    """TODO fields: sentiment, confidence, summary, themes: list[str],
       severity: int (Field ge=1 le=5), suggested_category: str"""
    ...

def build_analysis_chain(provider: str = "anthropic"):
    """
    TODO:
      1. Create a ChatPromptTemplate (system + human) for the analysis task.
      2. init_chat_model(...) for the given provider  (this is the one-line-swap magic).
      3. Bind structured output to ReviewAnalysis (with_structured_output).
      4. Return the composed chain:  prompt | model_with_structure
    Concept: LCEL pipes. The chain returns a ReviewAnalysis directly — no manual JSON parsing.
    """
    ...
```

**Done when:** same review → richer `ReviewAnalysis` via the chain; switching provider is literally one argument change and the chain still works.

---

## Day 3 — Stage 2: RAG for grounded solutions (naive → measured → fixed)

**Concept:** the "suggest a solution" half of your project. The whole skill is retrieval quality — and you MEASURE it. Also: turn on tracing today (Stage 7 says start early).

**`src/ingest.py`**
```python
def load_kb(kb_dir: str) -> list[dict]:
    """Read every file in data/kb/. Return [{'source': filename, 'text': ...}]. TODO."""
    ...

def chunk(docs: list[dict], size: int, overlap: int) -> list[dict]:
    """Split docs into chunks, keeping the source in metadata.
    TODO start with fixed-size. On the upgrade pass, try structure-aware (split on headings)."""
    ...

def build_index(chunks: list[dict]):
    """Embed chunks and store in Chroma (persistent). TODO: create collection, add texts+metadata."""
    ...
```

**`src/rag.py`**
```python
def retrieve(query: str, k: int = 5) -> list[dict]:
    """Naive first: embed query, vector-search top-k from Chroma. TODO."""
    ...

def suggest_solution(analysis: "ReviewAnalysis") -> dict:
    """Build a retrieval query from analysis.key_issues -> retrieve -> ask the model to draft a
    resolution GROUNDED ONLY in retrieved chunks, citing sources. TODO.
    Concept: if the answer isn't in the chunks, it should say so — not hallucinate."""
    ...
```

**`eval/retrieval_eval.py`**  ← the part that puts you ahead of 80% of people
```python
# TODO: write 15-20 test cases: {issue_query, expected_source_filename}.
def hit_rate(k: int) -> float:
    """For each test case, retrieve top-k, check if expected source appears. Return fraction hit.
    TODO. Run it, WRITE DOWN the number and which queries failed and why."""
    ...
```

**Then the upgrade pass:**
```python
def retrieve_hybrid(query: str, k_candidates: int = 20, k_final: int = 5) -> list[dict]:
    """
    TODO:
      1. BM25 keyword search (rank_bm25) over chunks -> candidates.
      2. Vector search -> candidates.
      3. Fuse with Reciprocal Rank Fusion.
      4. Rerank the ~20 fused candidates with a cross-encoder (sentence-transformers) -> keep top 5.
    Then re-run hit_rate() and record before vs after. That before/after IS your exit criterion.
    """
    ...
```

**Done when:** you have a recorded before/after hit rate; suggestions cite real KB files; tracing (LangSmith or Langfuse) is on and you can see each retrieval.

---

## Day 4 — Stage 3: Tools — hand-written loop, then MCP

**Concept:** run the tool loop yourself before a framework runs it for you. Every agent bug later is a tool bug underneath.

**`src/tools.py`**
```python
def search_knowledge_base(query: str) -> str:
    """Wrap your Day 3 retrieve_hybrid. TODO."""
    ...
def lookup_order(order_id: str) -> str:
    """Read data/orders.json, return the record or 'not found'. TODO."""
    ...
def escalate_ticket(review_id: str, reason: str) -> str:
    """Append a ticket to data/tickets.jsonl, return confirmation. TODO."""
    ...

TOOL_SCHEMAS = [...]  # TODO: JSON schema + a CLEAR description per tool.
                      # The description is what the model reads to choose — write it carefully.
```

**`src/tool_loop.py`** — NO agent abstraction
```python
def run_tool_loop(review: str, max_steps: int = 6) -> str:
    """
    TODO the loop by hand:
      1. Send review + TOOL_SCHEMAS to the model.
      2. If the response is a tool call: parse name+args, call the real function,
         append the result as a tool-result message, loop.
      3. If it's a final text answer: return it.
      4. Stop at max_steps (guard against infinite loops).
    Concept: YOU decide when to stop. Feel this before Stage 4 automates it.
    """
    ...
```

**`src/mcp_server.py`** — expose the SAME tools over MCP
```python
# TODO: use the MCP Python SDK to register search_knowledge_base / lookup_order / escalate_ticket
# as an MCP server. Then connect a client and call one. 
# Concept: what portability did MCP buy you vs the hand-wired version?
```

**Done when:** the hand loop resolves a review using tools; the same tools are callable over MCP.

---

## Day 5 — Stage 4: High-level agent, then deliberately break it

**Concept:** let the loop run itself — and *watch where it breaks*. The failures are the entire reason Stage 5 exists.

**`src/agent.py`**
```python
from langchain.agents import create_agent   # current 1.x API — NOT create_react_agent/AgentExecutor

def build_agent():
    """TODO: create_agent(model, tools=[...]) with your 3 tools wrapped as LangChain tools.
    Give it a system prompt describing the review-triage job."""
    ...
```

**`FAILURES.md`** — run these break-tests and log every failure mode:
- feed an **ambiguous** review ("it's fine I guess but also not")
- make `lookup_order` **throw** on purpose — does the agent recover or die silently?
- give a task needing **more steps than it'll take** — does it stop early / loop?

**Done when:** agent resolves normal reviews AND you have a concrete written list of how it failed. If you now *want* real state control — good, that's the point.

---

## Day 6 — Stage 5: LangGraph state machine (the payoff)

**Concept:** model the agent as a state machine so it can branch on severity, retry, pause for approval, and survive a restart.

**`src/graph.py`**
```python
from typing import TypedDict, Annotated
# from langgraph.graph import StateGraph, START, END
# from langgraph.checkpoint... import a checkpointer
# from langgraph.types import interrupt

class State(TypedDict):
    """TODO design this — the steepest, most important part. Fields like:
       review: str
       analysis: ReviewAnalysis | None
       retrieved: list | None
       draft_response: str | None
       status: str            # 'new'|'drafted'|'escalated'|'approved'|'sent'
    Concept: the schema IS the design. Don't copy an example — reason it out."""
    ...

# Nodes (each is a function State -> partial State):
def classify_node(state): ...      # TODO: run Day 2 chain, set analysis
def retrieve_node(state): ...      # TODO: run Day 3 RAG, set retrieved + draft_response
def escalate_node(state): ...      # TODO: call escalate_ticket, set status
def approval_node(state):
    """TODO: interrupt() here to PAUSE for human approval before sending a response
       to an angry customer. Resume applies the human's decision."""
    ...
def send_node(state): ...

def route_by_severity(state) -> str:
    """Conditional edge: severity >= 4 -> 'escalate', else 'retrieve'. TODO."""
    ...

def build_graph():
    """TODO: wire nodes + edges + the conditional edge + a checkpointer (so it's durable).
    Add a retry path when a tool node fails."""
    ...
```

**The money demo:** start processing a severe review → it hits the `interrupt()` and pauses → **kill the process** → restart → **resume from the checkpoint** and finish. If it survives that, you've met the exit criterion most people never reach.

**Done when:** angry reviews pause for approval; the run survives a process restart mid-task.

---

## Day 7 — Stage 6 (light) + Stage 7 + SHIP  *(drop Stage 6 if time's tight)*

**Stage 6 — multi-agent (stretch), `src/supervisor.py`**
Split into a **Triage** subagent (classify + severity) and a **Solution** subagent (RAG + draft) behind a **supervisor** that routes. Then do the honest part: compare cost + latency + reliability vs. your single Day-6 graph. **Write the verdict.** Usually the single well-scoped graph wins — proving that to yourself is the lesson.

**Stage 7 — eval + observability, `eval/`**
- You already have `retrieval_eval.py`. Now add a **scored end-to-end test set** (reviews → expected sentiment/severity) and a script that **fails (exit code 1) if the score drops** below a threshold.
- Prove it: make a prompt change that *degrades* quality, run the eval, watch it block. That's a CI gate.
- Confirm tracing lets you click from a bad final answer back to the exact node/retrieval that caused it.

**Ship it**
- README: architecture diagram, a demo GIF, your **before/after RAG numbers**, and your `FAILURES.md` insights.
- Deploy (Railway/Render/Fly). Real URL. Post one short technical write-up on the hardest bug (probably the state schema or retrieval).

**Done when:** a regression is caught automatically; you can trace any bad answer to its step; the repo is public.

---

## If you fall behind
Priority order to protect: **Day 1 → 2 → 3 → 6**. Those four (raw → chain → RAG → LangGraph) are the irreplaceable spine. Days 4–5 make 6 make sense but can be compressed. Day 7's Stage 6 is fully optional. Never skip Day 3's *measurement* — the before/after eval is the single most differentiating thing you'll build all week.

## Practice discipline (all week)
1. Commit at the end of every day with a message describing what you learned, not just what you did.
2. When stuck >20 min, read the actual library source, not another tutorial.
3. Use AI as a **code reviewer** ("critique this like a senior engineer"), never as the author — you already committed to this, it's why you'll actually learn it.
4. Keep `FAILURES.md` growing — it's your interview story bank.
