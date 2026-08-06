from src.rag import retrieve

from typing import Callable

TEST_CASES = [
    {"query": "My order arrived broken and I want a replacement", "expected_source": "damaged_item_guide.md"},
    {"query": "It's been 10 days and my package still hasn't arrived", "expected_source": "shipping_delay_faq.md"},
    {"query": "I was charged twice for the same order", "expected_source": "billing_errors.txt"},
    {"query": "I can't log into my account after the app update", "expected_source": "login_troubleshooting.md"},
    {"query": "The app keeps crashing when I try to upload a photo", "expected_source": "bug_reporting_process.txt"},
    {"query": "Does this product come with a warranty?", "expected_source": "warranty_terms.md"},
    {"query": "I've contacted support three times and nobody is helping me", "expected_source": "escalation_process.md"},
    {"query": "I want to return this item, it doesn't fit", "expected_source": "return_exchange_policy.txt"},
    {"query": "Where is my package right now?", "expected_source": "order_tracking_faq.md"},
    {"query": "Can you add a dark mode to the app?", "expected_source": "feature_requests.txt"},
    {"query": "This product feels cheap for the price I paid", "expected_source": "quality_complaints_handling.md"},
    {"query": "How do I get my money back for this order?", "expected_source": "refund_policy.md"},
    {"query": "What payment methods do you accept?", "expected_source": "payment_methods.md"},
    {"query": "How do I delete my account and my data?", "expected_source": "account_privacy.txt"},
    {"query": "The instructions in the box didn't explain how to set this up", "expected_source": "product_setup_guide.txt"},
    {"query": "Tracking says delivered but I never got my package", "expected_source": "order_tracking_faq.md"},
    {"query": "My battery dies really fast, is that covered?", "expected_source": "warranty_terms.md"},
    {"query": "I keep getting transferred between agents and nothing gets solved", "expected_source": "escalation_process.md"},
]


def hit_rate(k: int, retrieve_fn: Callable[[str, int], list[dict]] = retrieve) -> float:
    """For each test case, retrieve top-k, check if expected source appears. Return fraction hit.
    Prints a HIT/MISS line per case so you can see exactly which queries failed.
    Pass retrieve_fn=retrieve_hybrid to measure the upgraded retrieval instead of the baseline."""
    hits = 0
    for case in TEST_CASES:
        results = retrieve_fn(case["query"], k)
        sources = [r["source"] for r in results]
        hit = case["expected_source"] in sources
        hits += int(hit)
        status = "HIT " if hit else "MISS"
        print(f"[{status}] {case['query']!r} -> expected {case['expected_source']}, got {sources}")

    rate = hits / len(TEST_CASES)
    print(f"\nhit_rate@{k}: {rate:.2f} ({hits}/{len(TEST_CASES)})")
    return rate


if __name__ == "__main__":
    hit_rate(5)
