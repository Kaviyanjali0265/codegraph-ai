# Graph extraction eval: LLM name extraction + caller/callee Jaccard on impact queries.
# Reports two scores:
#   graph-only  — traversal using the *expected* function name (tests AST + graph + BFS)
#   end-to-end  — traversal using the *extracted* name (tests full pipeline)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.impact_analyzer.main import EXTRACT_PROMPT
from core.graph_store import GraphStore
from core.ollama_client import llm
from evals.dataset import EVAL_DATASET


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def _traverse(graph: GraphStore, fn_name: str, expected_callers: set, expected_callees: set, in_graph: bool = True) -> tuple[float, float]:
    if not in_graph:
        return 0.0, 0.0
    callers = {n.name for n in graph.find_callers(fn_name)}
    callees = {n.name for n in graph.find_callees(fn_name)}
    return _jaccard(callers, expected_callers), _jaccard(callees, expected_callees)


def run() -> dict:
    graph = GraphStore()
    if not graph.load():
        print("=== EXTRACTION + GRAPH EVAL === SKIPPED (graph not built — run ingest first)")
        return {}

    impact_rows = [r for r in EVAL_DATASET if r["expected_query_type"] == "impact_analysis"]

    extract_correct = 0
    graph_only_cj, graph_only_dj = [], []
    e2e_cj, e2e_dj = [], []
    per_query = []

    print("=== EXTRACTION + GRAPH EVAL ===")
    for row in impact_rows:
        expected_fn = row["expected_function"]
        expected_callers = set(row.get("expected_callers", []))
        expected_callees = set(row.get("expected_callees", []))

        # Step 1: graph-only — use expected function name directly
        go_cj, go_dj = _traverse(graph, expected_fn, expected_callers, expected_callees)
        graph_only_cj.append(go_cj)
        graph_only_dj.append(go_dj)

        # Step 2: LLM extraction (uses same prompt as impact_analyzer agent)
        extracted = llm(EXTRACT_PROMPT.format(query=row['query'])).strip().strip('"').strip("'")
        extraction_ok = extracted == expected_fn
        if extraction_ok:
            extract_correct += 1

        # Step 3: end-to-end — traverse with what the LLM gave us
        # score 0 if extracted name doesn't exist in graph (avoids both-empty → 1.0 inflation)
        extracted_in_graph = graph._resolve(extracted) is not None
        e2e_c, e2e_d = _traverse(graph, extracted, expected_callers, expected_callees, in_graph=extracted_in_graph)
        e2e_cj.append(e2e_c)
        e2e_dj.append(e2e_d)

        per_query.append({
            "query": row["query"],
            "expected_fn": expected_fn,
            "extracted": extracted,
            "extraction_ok": extraction_ok,
            "graph_only_caller_jaccard": round(go_cj, 3),
            "graph_only_callee_jaccard": round(go_dj, 3),
            "e2e_caller_jaccard": round(e2e_c, 3),
            "e2e_callee_jaccard": round(e2e_d, 3),
        })

        ext_mark = "✓" if extraction_ok else "✗"
        print(f"  {ext_mark} extract: [{extracted}]  (expected: {expected_fn})")
        print(f"    graph-only  callers J={go_cj:.2f}  callees J={go_dj:.2f}")
        print(f"    end-to-end  callers J={e2e_c:.2f}  callees J={e2e_d:.2f}")

    n = len(impact_rows)
    extraction_acc = extract_correct / n

    print(f"\nExtraction accuracy        : {extract_correct}/{n} = {extraction_acc:.1%}")
    print(f"Graph-only  caller Jaccard : {sum(graph_only_cj)/n:.3f}  (tests AST + graph + BFS)")
    print(f"Graph-only  callee Jaccard : {sum(graph_only_dj)/n:.3f}")
    print(f"End-to-end  caller Jaccard : {sum(e2e_cj)/n:.3f}  (tests full pipeline)")
    print(f"End-to-end  callee Jaccard : {sum(e2e_dj)/n:.3f}")

    return {
        "extraction_accuracy": extraction_acc,
        "graph_only_caller_jaccard": sum(graph_only_cj) / n,
        "graph_only_callee_jaccard": sum(graph_only_dj) / n,
        "e2e_caller_jaccard": sum(e2e_cj) / n,
        "e2e_callee_jaccard": sum(e2e_dj) / n,
        "per_query": per_query,
    }
