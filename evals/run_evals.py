# Runs all eval levels and prints a summary. Use --skip-generation --json for CI.

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals import eval_generation, eval_graph, eval_retrieval, eval_routing

SEP = "=" * 60
RESULTS_PATH = Path(__file__).parent / "results.json"


def main():
    parser = argparse.ArgumentParser(description="CodeGraph AI Eval Suite")
    parser.add_argument("--skip-generation", action="store_true",
                        help="Skip generation eval (requires all 4 services running)")
    parser.add_argument("--json", action="store_true",
                        help="Save results to evals/results.json for the dashboard")
    args = parser.parse_args()

    results: dict = {"timestamp": datetime.utcnow().isoformat()}

    print(SEP)
    results["routing"] = eval_routing.run()

    print("\n" + SEP)
    results["retrieval"] = eval_retrieval.run()

    print("\n" + SEP)
    results["graph"] = eval_graph.run()

    if not args.skip_generation:
        print("\n" + SEP)
        results["generation"] = eval_generation.run()
    else:
        print("\n[Generation eval skipped — omit --skip-generation to run it]")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + SEP)
    print("SUMMARY")
    print(SEP)

    r = results.get("routing", {})
    if r:
        print(f"Routing   accuracy     : {r['correct']}/{r['total']} = {r['accuracy']:.1%}")

    r = results.get("retrieval", {})
    if r:
        print(f"Retrieval Recall@k     : {r['mean_recall_at_k']:.3f}")
        print(f"Retrieval MRR          : {r['mrr']:.3f}")

    r = results.get("graph", {})
    if r:
        print(f"Graph     extraction        : {r['extraction_accuracy']:.1%}")
        print(f"Graph-only caller Jaccard   : {r['graph_only_caller_jaccard']:.3f}")
        print(f"Graph-only callee Jaccard   : {r['graph_only_callee_jaccard']:.3f}")
        print(f"End-to-end caller Jaccard   : {r['e2e_caller_jaccard']:.3f}")
        print(f"End-to-end callee Jaccard   : {r['e2e_callee_jaccard']:.3f}")

    r = results.get("generation", {})
    if r:
        print(f"Generation groundedness: {r['mean_groundedness']:.2f}/5")
        print(f"Generation relevance   : {r['mean_relevance']:.2f}/5")

    if args.json:
        with open(RESULTS_PATH, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved → {RESULTS_PATH}")
        print("Dashboard: http://localhost:8000/ui/evals.html")


if __name__ == "__main__":
    main()
