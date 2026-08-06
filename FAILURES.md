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
