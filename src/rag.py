import chromadb
from chromadb import PersistentClient
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from .models import ReviewAnalysis

load_dotenv()

_cross_encoder = None


def _get_cross_encoder() -> CrossEncoder:
    """Lazy-load the cross-encoder once and reuse it - it's slow to load."""
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def retrieve(query: str, k: int = 5) -> list[dict]:
    """Naive first: embed query, vector-search top-k from Chroma. TODO."""
    client = chromadb.PersistentClient("data/chroma")
    collection = client.get_or_create_collection("Knowledge_base")
    response = collection.query(query_texts=[query], n_results=k)
    results: list[dict] = []
    for text, metadata, distance in zip(
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        ans = {
            "text": text,
            "source": metadata["source"],
            "distance": distance,
        }

        results.append(ans)

    return results

def suggest_solution(analysis: ReviewAnalysis) -> dict:
    """Build a retrieval query from analysis.themes -> retrieve -> ask the model to draft a
    resolution GROUNDED ONLY in retrieved chunks, citing sources.
    Concept: if the answer isn't in the chunks, it should say so - not hallucinate."""

    query = ", ".join(analysis.themes) if analysis.themes else analysis.summary
    retrieved = retrieve(query, k=5)

    context = "\n\n".join(f"[Source: {r['source']}]\n{r['text']}" for r in retrieved)

    prompt = f"""You are drafting a resolution for a customer support review.

Customer review summary: {analysis.summary}
Sentiment: {analysis.sentiment}
Key issues: {query}

Use ONLY the knowledge base excerpts below to draft a resolution. Do not use any outside
knowledge. If the excerpts do not cover the customer's issue, say so explicitly instead of
guessing or making something up.

{context}

Respond with a short, empathetic resolution a support agent could send to the customer, and on a
final line list the exact source filenames you grounded your answer in, like:
Sources: refund_policy.md, damaged_item_guide.md
"""

    model = init_chat_model("google_genai:gemini-3.5-flash")
    response = model.invoke(prompt)

    if isinstance(response.content, str):
        resolution_text = response.content
    else:
        resolution_text = "".join(
            block.get("text", "")
            for block in response.content
            if isinstance(block, dict)
        )

    return {
        "resolution": resolution_text,
        "sources": sorted({r["source"] for r in retrieved}),
    }


def retrieve_hybrid(query: str, k_candidates: int = 20, k_final: int = 5) -> list[dict]:
    """
    1. BM25 keyword search (rank_bm25) over chunks -> candidates.
    2. Vector search -> candidates.
    3. Fuse with Reciprocal Rank Fusion.
    4. Rerank the ~20 fused candidates with a cross-encoder (sentence-transformers) -> keep top 5.
    """
    client = chromadb.PersistentClient("data/chroma")
    collection = client.get_or_create_collection("Knowledge_base")

    # Pull the whole corpus - fine at this scale (a few dozen chunks), BM25 needs the full set.
    corpus = collection.get(include=["documents", "metadatas"])
    all_ids = corpus["ids"]
    all_texts = corpus["documents"]
    all_metadatas = corpus["metadatas"]
    id_to_text = dict(zip(all_ids, all_texts))
    id_to_source = {doc_id: meta["source"] for doc_id, meta in zip(all_ids, all_metadatas)}

    # --- 1. BM25 keyword search ---
    tokenized_corpus = [text.lower().split() for text in all_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())
    bm25_order = sorted(range(len(all_ids)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_ranked_ids = [all_ids[i] for i in bm25_order[:k_candidates]]

    # --- 2. Vector search ---
    n = min(k_candidates, len(all_ids))
    vector_response = collection.query(query_texts=[query], n_results=n)
    vector_ranked_ids = vector_response["ids"][0]

    # --- 3. Reciprocal Rank Fusion ---
    RRF_K = 60
    fused_scores: dict[str, float] = {}
    for ranked_ids in (bm25_ranked_ids, vector_ranked_ids):
        for rank, doc_id in enumerate(ranked_ids):
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    fused_ranking = sorted(fused_scores, key=lambda doc_id: fused_scores[doc_id], reverse=True)
    fused_ranking = fused_ranking[:k_candidates]

    # --- 4. Cross-encoder rerank ---
    cross_encoder = _get_cross_encoder()
    pairs = [(query, id_to_text[doc_id]) for doc_id in fused_ranking]
    rerank_scores = cross_encoder.predict(pairs)

    reranked = sorted(zip(fused_ranking, rerank_scores), key=lambda pair: pair[1], reverse=True)
    top = reranked[:k_final]

    return [
        {"text": id_to_text[doc_id], "source": id_to_source[doc_id], "score": float(score)}
        for doc_id, score in top
    ]
