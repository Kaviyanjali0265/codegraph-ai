# LLM-as-judge eval for final answer quality. Requires all 4 services running.

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from core.ollama_client import llm_classify as llm_judge
from evals.dataset import EVAL_DATASET

ORCHESTRATOR_URL = "http://localhost:8000"
API_KEY = "key-dev-001"

# 2 per type — indices into EVAL_DATASET
GENERATION_SUBSET = [
    EVAL_DATASET[0],   # code_analysis:    "What does place_order do?"
    EVAL_DATASET[2],   # code_analysis:    "How are users notified?"
    EVAL_DATASET[6],   # doc_generation:   "Generate docs for the refund function"
    EVAL_DATASET[7],   # doc_generation:   "Write documentation for cancel_order"
    EVAL_DATASET[12],  # impact_analysis:  "What breaks if charge_card changes?"
    EVAL_DATASET[14],  # impact_analysis:  "What is affected if get_product changes?"
]


def _judge(query: str, answer: str, sources: list[str]) -> dict:
    sources_text = "\n".join(f"- {s}" for s in sources) if sources else "none"
    prompt = (
        "You are evaluating an AI assistant's answer to a code question.\n\n"
        f"Question: {query}\n"
        f"Retrieved sources (functions/modules used to answer):\n{sources_text}\n\n"
        f"Answer: {answer}\n\n"
        "Score on two dimensions, each 1-5:\n"
        "GROUNDEDNESS: Is the answer consistent with the retrieved sources? "
        "(1=contradicts sources or ignores them, 5=fully grounded in the sources)\n"
        "RELEVANCE: Does the answer directly address what was asked? "
        "(1=off-topic, 5=directly on-point)\n\n"
        "Reply in this exact format:\n"
        "GROUNDEDNESS: <1-5>\n"
        "RELEVANCE: <1-5>\n"
        "REASON: <one sentence>"
    )
    result = llm_judge(prompt)
    g = re.search(r"GROUNDEDNESS:\s*(\d)", result)
    r = re.search(r"RELEVANCE:\s*(\d)", result)
    reason = re.search(r"REASON:\s*(.+)", result)
    if not g or not r:
        print(f"[judge] parse failed — raw output: {result!r}")
        return None
    return {
        "groundedness": int(g.group(1)),
        "relevance": int(r.group(1)),
        "reason": reason.group(1).strip() if reason else "",
    }


def run() -> dict:
    print("=== GENERATION EVAL (LLM-as-judge) ===")
    print("Requires: orchestrator on :8000, agents on :8001/:8002/:8003, Ollama\n")

    groundedness_scores, relevance_scores = [], []

    for row in GENERATION_SUBSET:
        try:
            resp = httpx.post(
                f"{ORCHESTRATOR_URL}/query",
                json={"query": row["query"], "session_id": "eval"},
                headers={"x-api-key": API_KEY},
                timeout=180.0,
            )
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("answer", "")
            agent_used = data.get("agent_used", "")
            sources = data.get("sources", [])
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            print(f"  ✗ FAILED  {row['query'][:50]}\n    {exc}\n")
            continue

        scores = _judge(row["query"], answer, sources)
        if scores is None:
            print(f"  ✗ JUDGE PARSE FAILED  {row['query'][:50]}\n")
            continue
        groundedness_scores.append(scores["groundedness"])
        relevance_scores.append(scores["relevance"])

        print(f"  Query  : {row['query']}")
        print(f"  Agent  : {agent_used}")
        print(f"  G={scores['groundedness']}/5  R={scores['relevance']}/5  {scores['reason']}")
        print()

    if not groundedness_scores:
        print("No results — are the services running?")
        return {}

    mean_g = sum(groundedness_scores) / len(groundedness_scores)
    mean_r = sum(relevance_scores) / len(relevance_scores)
    print(f"Mean Groundedness : {mean_g:.2f}/5")
    print(f"Mean Relevance    : {mean_r:.2f}/5")
    return {"mean_groundedness": mean_g, "mean_relevance": mean_r}
