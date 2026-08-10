"""Scored end-to-end eval: reviews -> expected sentiment/severity.
Run directly (`python -m eval.e2e_eval`) as a CI gate - exits 1 if the score drops below THRESHOLD.
"""
import sys

from src.chain import build_analysis_chain

THRESHOLD = 0.80

# severity is somewhat subjective, so it's scored with tolerance; sentiment must match exactly.
SEVERITY_TOLERANCE = 1

TEST_CASES = [
    {"review": "Absolutely love this product! It arrived early and works perfectly.", "sentiment": "positive", "severity": 1},
    {"review": "Terrible experience. The item stopped working after two days.", "sentiment": "negative", "severity": 4},
    {"review": "Delivery was fast but the packaging was damaged.", "sentiment": "negative", "severity": 3},
    {"review": "Customer support resolved my issue quickly. Very satisfied.", "sentiment": "positive", "severity": 1},
    {"review": "I want a refund. The product arrived broken.", "sentiment": "negative", "severity": 4},
    {"review": "Five stars! Exceeded all my expectations.", "sentiment": "positive", "severity": 1},
    {"review": "The app crashes every time I try to upload a file.", "sentiment": "negative", "severity": 4},
    {"review": "Shipping took two weeks longer than promised.", "sentiment": "negative", "severity": 3},
    {"review": "I was charged twice for my order.", "sentiment": "negative", "severity": 4},
    {"review": "Support kept transferring me between agents without solving anything.", "sentiment": "negative", "severity": 4},
    {"review": "Works exactly as advertised. Highly recommend.", "sentiment": "positive", "severity": 1},
    {"review": "It's fine, I guess. Not great, not terrible.", "sentiment": "neutral", "severity": 2},
    {"review": "Product quality is excellent, but customer service is awful.", "sentiment": "negative", "severity": 3},
    {"review": "This is the worst purchase I've made all year.", "sentiment": "negative", "severity": 5},
    {"review": "Wow, another 'premium' product that fails on day one. Fantastic.", "sentiment": "negative", "severity": 5},
    {"review": "The product itself is good, but shipping was extremely slow and support never replied.", "sentiment": "negative", "severity": 4},
    {"review": "My payment failed even though my bank confirmed the transaction.", "sentiment": "negative", "severity": 4},
    {"review": "Please add dark mode and offline support in the next release.", "sentiment": "neutral", "severity": 1},
]


def score() -> float:
    chain = build_analysis_chain()
    hits = 0
    for case in TEST_CASES:
        analysis = chain.invoke({"review": case["review"]})
        sentiment_ok = analysis.sentiment == case["sentiment"]
        severity_ok = abs(analysis.severity - case["severity"]) <= SEVERITY_TOLERANCE
        hit = sentiment_ok and severity_ok
        hits += int(hit)
        status = "HIT " if hit else "MISS"
        print(
            f"[{status}] {case['review'][:60]!r} -> expected ({case['sentiment']}, sev={case['severity']}), "
            f"got ({analysis.sentiment}, sev={analysis.severity})"
        )

    rate = hits / len(TEST_CASES)
    print(f"\nscore: {rate:.2f} ({hits}/{len(TEST_CASES)}), threshold: {THRESHOLD:.2f}")
    return rate


if __name__ == "__main__":
    result = score()
    if result < THRESHOLD:
        print(f"FAIL: score {result:.2f} is below threshold {THRESHOLD:.2f}")
        sys.exit(1)
    print("PASS")
    sys.exit(0)
