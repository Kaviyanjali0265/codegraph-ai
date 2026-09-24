# Retrieval eval: Recall@k and MRR against ChromaDB. Requires ingest to have run.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ollama_client import embed
from core.vectorstore import VectorStore
from evals.dataset import EVAL_DATASET

K_BY_TYPE = {
    "code_analysis": 4,
    "doc_generation": 3,
    "impact_analysis": 3,
}


def _recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for e in expected if e in top_k)
    return hits / len(expected) if expected else 0.0


def _reciprocal_rank(retrieved: list[str], expected: list[str]) -> float:
    for i, name in enumerate(retrieved):
        if name in expected:
            return 1.0 / (i + 1)
    return 0.0


def run() -> dict:
    store = VectorStore()
    recalls, rrs = [], []
    per_query = []

    print("=== RETRIEVAL EVAL ===")
    for row in EVAL_DATASET:
        k = K_BY_TYPE[row["expected_query_type"]]
        results = store.query(embed(row["query"]), n_results=k)
        retrieved_names = [r["metadata"].get("name", "") for r in results]

        r_at_k = _recall_at_k(retrieved_names, row["expected_functions"], k)
        rr = _reciprocal_rank(retrieved_names, row["expected_functions"])
        recalls.append(r_at_k)
        rrs.append(rr)
        per_query.append({
            "query": row["query"],
            "k": k,
            "recall": round(r_at_k, 3),
            "rr": round(rr, 3),
            "expected": row["expected_functions"],
            "retrieved": retrieved_names,
        })

        status = "✓" if r_at_k == 1.0 else "~" if r_at_k > 0 else "✗"
        print(f"  {status} R@{k}={r_at_k:.2f}  RR={rr:.2f}  {row['query'][:45]}")
        print(f"      expected={row['expected_functions']}")
        print(f"      retrieved={retrieved_names}")

    mean_recall = sum(recalls) / len(recalls)
    mrr = sum(rrs) / len(rrs)
    print(f"\nMean Recall@k : {mean_recall:.3f}")
    print(f"MRR           : {mrr:.3f}")

    return {"mean_recall_at_k": mean_recall, "mrr": mrr, "per_query": per_query}
