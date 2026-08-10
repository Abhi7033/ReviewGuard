# Failure Log

Every entry: what broke, the exact input, why (root cause), what fixed it (or didn't yet).
This is the interview story bank — keep it growing from Day 1 onward, not just Day 5.

## Day 3 — retrieval quality (naive vs hybrid)

hit_rate@5 was a perfect 1.00 (18/18) — useless as a metric, no headroom to show improvement.
Switched to hit_rate@1 for a metric that actually discriminates.

- BEFORE (naive vector search only), hit_rate@1: 0.83 (15/18). 3 misses, all between
  topically-adjacent docs: "contacted support 3x" -> login_troubleshooting.md instead of
  escalation_process.md; "where is my package" -> shipping_delay_faq.md instead of
  order_tracking_faq.md; "want to return, doesn't fit" -> damaged_item_guide.md instead of
  return_exchange_policy.txt.
- AFTER (BM25 + vector + Reciprocal Rank Fusion + cross-encoder rerank), hit_rate@1: 0.94 (17/18).
  Fixed 2 of the 3 misses (escalation, package tracking).
- Still misses: "want to return, doesn't fit" -> damaged_item_guide.md. Root cause isn't a
  retrieval algorithm problem — "return, doesn't fit" and "damaged item" are genuinely close in
  *meaning* (both are "something's wrong with what I got"), and no reranking fixes a KB that
  doesn't clearly separate "wrong size" from "arrived broken." The real fix is better KB content,
  not better retrieval — a lesson in itself: retrieval quality is capped by knowledge base
  quality, not just algorithm choice.

## Day 4 — free-tier quota is per-project, not per-key

Testing the hand-written tool loop, hit repeated 503s on gemini-3.5-flash, then a hard 429:
`GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit: 20`. Generated a brand new API key
from the same Google account expecting a fresh quota — same 429, same limit: 20. The daily quota
is scoped to the underlying Google Cloud project, not the individual API key, so a new key from
the same account/project shares the same exhausted bucket. Only a genuinely different account
(different project) had separate quota. Lesson: rotating keys is not the same as rotating
quota — check what the limit is actually scoped to before assuming a new credential helps.

Also: verified the MCP SDK's actual API from the installed package instead of trusting my own
memory of the library. My prior knowledge said `FastMCP` from `mcp.server.fastmcp` - the actually
installed version (2.0.0) uses `MCPServer` from `mcp.server.mcpserver.server` instead. Same
lesson as Day 2's Vertex AI mixup: verify against what's actually installed, not what you
remember, especially for fast-moving SDKs.

## Day 5 — create_agent break-tests

Confirmed create_agent(...) returns a real langgraph.graph.state.CompiledStateGraph - it's a
pre-built LangGraph graph, not a separate paradigm from Day 6.

**Break-test 1: ambiguous review ("It's fine, I guess. Not great, not terrible.")**
Did not fail outright - it answered reasonably in the end (asked for specifics, correctly cited
the 30-day return/exchange policy). But it took 6 consecutive search_knowledge_base calls to get
there, several with near-duplicate queries ("neutral review", "review guidelines", "neutral
feedback") that re-fetched chunks it already had. Root cause: with no concrete issue to search
for, the model doesn't recognize "there's no clear signal here" and instead thrashes, trying
slightly different phrasings hoping something relevant turns up. This isn't a framework problem
specifically - a hand-written loop wouldn't have stopped this either, nothing prevents a model
from calling the same tool repeatedly - but the framework hid it from view until the full message
list was printed after the fact. Real cost: 6 wasted API calls against an already-tight daily
quota, for a review that needed zero tool calls to answer well.

**Break-test 2: make lookup_order throw on purpose (mocked, tools.py untouched)**
Patched lookup_order to raise RuntimeError("database connection lost"), invoked the agent asking
about an order. Result: agent.invoke() CRASHED with the raw RuntimeError - the whole run died,
no graceful handling. Unlike Day 4's tool_loop.py, where *I* wrote the try/except that turns a
tool exception into a message the model can react to, create_agent does NOT catch tool exceptions
for you by default. An unhandled error inside any one tool takes down the entire agent run. This
is the clearest gap so far between "the framework runs the loop" and "the framework handles
everything you'd otherwise have to handle yourself" - it doesn't. Fix would be either wrapping
tool functions defensively (return an error string instead of raising) or finding create_agent's
actual error-handling hook, if one exists - worth digging into before this goes anywhere near
production.

Side note on testing method: my first attempt at this mock patched src.tools.lookup_order, which
silently did nothing - agent.py does `from .tools import lookup_order`, which binds its own
separate name at import time. Patching the original module doesn't touch a name another module
already imported by value. Had to patch src.agent.lookup_order instead - the name where it's
actually used, not where it's defined.

**Break-test 3: task needing more steps than allowed**
Forced config={'recursion_limit': 2} on the same multi-issue review that normally takes 6+ tool
calls. Result: GraphRecursionError, a clean named exception with a helpful message pointing at
docs - not a silent hang, not an infinite loop. But still a crash: no partial answer returned,
no graceful "ran out of steps, here's what I have so far" fallback like Day 4's max_steps guard
gave. Confirms create_agent really is built on LangGraph (the exception is literally
GraphRecursionError, a LangGraph-native error type).

**Synthesis across all three break-tests:** create_agent handles the mechanical parts of the
loop well (message threading, tool-call parsing, deciding when to stop normally), but every
failure mode defaults to "raise an exception and stop" rather than "recover gracefully" - that
recovery logic was something *I* had to write by hand in Day 4's tool_loop.py, and create_agent
doesn't do it for free. This is exactly the gap Day 6's LangGraph is supposed to close: instead
of a black-box loop that crashes on the exact failure modes you already know how to handle
yourself, build the graph explicitly so you control retries, error branches, and step limits
directly.

## Day 6 — LangGraph state machine

Confirmed both exit criteria live: a severe review (severity=5) correctly routed to escalate ->
approval, hit interrupt(), and genuinely paused - the returned state had status='escalated',
approved=None, and an __interrupt__ key, with no progress to send_node. Resumed that exact run in
a completely separate `python3 -c` process (not just a new function call - a fresh process with
zero memory of the first run), giving it only the same thread_id, and it picked up exactly at
approval_node, applied the resumed decision, and completed to status='sent'. This only worked
because the checkpointer is SqliteSaver (disk-backed) - LangGraph's InMemorySaver would not have
survived the process boundary, which is the actual point of the demo.

Real gotcha found on the resume run: `Deserializing unregistered type src.models.ReviewAnalysis
from checkpoint. This will be blocked in a future version.` LangGraph's checkpoint serialization
doesn't automatically trust arbitrary Python/Pydantic classes stored in State - putting a rich
ReviewAnalysis object directly into the graph's state works today but is flagged as something
that'll be blocked outright in a future langgraph-checkpoint version unless the type is
explicitly allowlisted. Not broken yet, but a real forward-compatibility risk: worth either
converting analysis to a plain dict before storing in State, or explicitly registering the type,
before relying on this in anything longer-lived than a demo.

Also confirmed the anti-hallucination grounding from Day 3 holds up inside the graph, not just in
isolation: a review about the app being "slow to load" - a topic with zero matching KB doc -
correctly got the response "the provided knowledge base excerpts do not contain any information
... I cannot draft a resolution" instead of a fabricated answer. Also revealed a real KB gap
(no general product-performance-feedback doc) worth adding later.

## Day 7 — eval/e2e_eval.py CI gate

Baseline: 18/18 test cases (sentiment exact match + severity within +/-1 tolerance), score 1.00,
well above the 0.80 threshold. PASS, exit code 0.

Proved the gate actually blocks a regression: injected a deliberately bad system-prompt change
("Always set severity to 1 regardless of how serious the issue seems") into chain.py, a realistic
kind of accidental prompt edit. Reran the eval - hit the 20/day Gemini quota again after only 4 of
18 cases, but those 4 already proved the point: both negative-review cases that should have scored
severity 3-4 collapsed to severity=1 exactly as the injected instruction demanded (2/2 misses on
exactly the field that was sabotaged; the 2 positive-review cases still passed since their real
severity was already 1, so the degradation didn't change their outcome). Reverted the prompt
immediately after (confirmed via empty `git diff`) rather than burn more quota chasing a complete
18/18 FAIL for a result the partial run already demonstrates: the eval script is sensitive to real
quality regressions, not just structurally passing/failing regardless of prompt content.

Running total on the Gemini free-tier daily cap: this is the fourth time in one day (Days 4, 5,
6-adjacent testing, and now Day 7) that the 20-requests/day limit on gemini-3.5-flash has blocked
iterative work mid-task. Every time, switching to a different Google account (not just a new key
on the same account/project) resolved it - but each fresh account only buys ~20 more requests
before hitting the same wall again. For any future work needing more than a handful of live model
calls in one sitting, this is worth solving properly (Groq's free tier has no equivalent daily
cap) rather than repeating the account-switch cycle.
