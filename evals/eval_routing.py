# Routing eval: checks classify_query returns the correct label across all 18 queries.

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.dataset import EVAL_DATASET
from orchestrator.graph import VALID_LABELS, classify_raw

LABELS = ["code_analysis", "impact_analysis", "doc_generation"]


def run() -> dict:
    correct = 0
    exact_count = 0   # model returned a valid label verbatim
    total = len(EVAL_DATASET)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_query = []

    print("=== ROUTING EVAL ===")
    for row in EVAL_DATASET:
        predicted, method, raw = classify_raw(row["query"])
        expected = row["expected_query_type"]
        confusion[expected][predicted] += 1
        hit = predicted == expected
        if hit:
            correct += 1
        if method == "exact":
            exact_count += 1
        per_query.append({
            "query": row["query"],
            "expected": expected,
            "predicted": predicted,
            "correct": hit,
            "method": method,
            "raw": raw,
        })
        status = "✓" if hit else "✗"
        method_tag = "" if method == "exact" else f" [{method}]"
        print(f"  {status} expected={expected:20} predicted={predicted:20}{method_tag}  {row['query'][:40]}")

    accuracy = correct / total
    valid_label_rate = exact_count / total

    print(f"\nAccuracy        : {correct}/{total} = {accuracy:.1%}  (was the label correct?)")
    print(f"Valid-label rate: {exact_count}/{total} = {valid_label_rate:.1%}  (did model return exact label?)")
    print("  These are two separate failures — format drift vs wrong choice.")

    print("\nConfusion matrix (rows=actual, cols=predicted):")
    header = f"{'':22}" + "".join(f"{l[:14]:>16}" for l in LABELS)
    print(header)
    for actual in LABELS:
        row_str = f"{actual:22}" + "".join(f"{confusion[actual][pred]:>16}" for pred in LABELS)
        print(row_str)

    confusion_plain = {a: {p: confusion[a][p] for p in LABELS} for a in LABELS}

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "valid_label_rate": valid_label_rate,
        "exact_count": exact_count,
        "confusion": confusion_plain,
        "per_query": per_query,
    }
