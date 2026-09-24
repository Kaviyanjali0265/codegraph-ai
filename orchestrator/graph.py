import re
import sys
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.guardrails import validate_input, validate_output
from core.memory import MemoryStore
from core.ollama_client import llm, llm_classify

from orchestrator.agent_client import get_client

MAX_REFLECTIONS = 2
REFLECTION_PASS_SCORE = 6


class OrchestratorState(TypedDict):
    query: str
    session_id: str
    enriched_query: str
    query_type: str
    agent_result: str
    sources: list[str]
    blocked: bool
    block_reason: str
    reflection_count: int
    reflection_score: int


def input_guardrail(state: OrchestratorState) -> dict:
    result = validate_input(state["query"])
    return {"blocked": not result.passed, "block_reason": result.reason}


def output_guardrail(state: OrchestratorState) -> dict:
    result = validate_output(state["agent_result"], state["sources"])
    if not result.passed:
        return {
            "agent_result": f"Response blocked: {result.reason}",
            "blocked": True,
            "block_reason": result.reason,
        }
    return {"blocked": False, "block_reason": ""}


def blocked_response(state: OrchestratorState) -> dict:
    return {"agent_result": f"Request blocked: {state['block_reason']}"}


def load_memory(state: OrchestratorState) -> dict:
    memory = MemoryStore()
    session_id = state["session_id"] or "default"

    history = memory.get_session_history(session_id)
    recent = "\n".join([f"Q: {h['query']}\nA: {h['answer']}" for h in history[-3:]])
    past = memory.retrieve_relevant(state["query"], n_results=2)
    long_term = "\n\n".join(past)

    parts = []
    if recent:
        parts.append(f"Recent conversation:\n{recent}")
    if long_term:
        parts.append(f"Relevant past context:\n{long_term}")
    parts.append(f"Current question: {state['query']}")

    return {"enriched_query": "\n\n".join(parts)}


def save_memory(state: OrchestratorState) -> dict:
    if state.get("agent_result") and not state.get("blocked"):
        memory = MemoryStore()
        memory.save(
            session_id=state["session_id"] or "default",
            query=state["query"],
            answer=state["agent_result"],
        )
    return {}


VALID_LABELS = {"code_analysis", "impact_analysis", "doc_generation"}

_CLASSIFY_PROMPT = """\
You are a query classifier. Pick exactly one label from the three below.

LABELS:
- code_analysis    : user wants to UNDERSTAND how code works (explain, describe, how does X work, what does X do)
- impact_analysis  : user wants to know WHAT BREAKS or WHAT DEPENDS on something (what breaks if X changes, what calls X, dependencies, affected by)
- doc_generation   : user wants you to WRITE or GENERATE documentation text (generate docs, write docstring, document this function)

KEY DISTINCTION:
- "What does X do?" -> code_analysis  (understanding, not writing docs)
- "Generate docs for X" -> doc_generation  (writing output)
- "What breaks if X changes?" -> impact_analysis  (dependency tracing)

Examples:
Query: What does save_order do?           -> code_analysis
Query: How does release_item work?        -> code_analysis
Query: How does notify_admin send alerts? -> code_analysis
Query: What breaks if update_stock changes?  -> impact_analysis
Query: What calls notify_admin?              -> impact_analysis
Query: Generate docs for release_item    -> doc_generation
Query: Write documentation for send_sms  -> doc_generation

Query: {query}

Reply with ONLY the label. No explanation."""


def classify_raw(query: str) -> tuple[str, str, str]:
    """Classify a query. Returns (label, method, raw_output).

    method values:
      'exact'   — model returned a valid label verbatim
      'default' — output unrecognised; fell back to code_analysis
    """
    raw = llm_classify(_CLASSIFY_PROMPT.format(query=query)).strip().lower()

    if raw in VALID_LABELS:
        return raw, "exact", raw

    # unrecognised — default but log it so failures aren't hidden
    print(f"[classify] unrecognised output: '{raw}' → defaulting to code_analysis")
    return "code_analysis", "default", raw


def classify_query(state: OrchestratorState) -> dict:
    label, _method, _raw = classify_raw(state["query"])
    return {"query_type": label}


def call_agent(state: OrchestratorState) -> dict:
    client = get_client(state["query_type"])
    response = client.call(query=state["enriched_query"])
    return {"agent_result": response.result, "sources": response.sources}


def reflect(state: OrchestratorState) -> dict:
    prompt = f"""Evaluate this answer to the question below.

Question: {state["query"]}
Answer: {state["agent_result"]}

Is the answer specific, relevant, and complete?
Reply in this exact format:
SCORE: <number 1-10>
FEEDBACK: <one sentence on what is missing or wrong>"""

    result = llm(prompt)

    score = REFLECTION_PASS_SCORE
    feedback = ""

    score_match = re.search(r"SCORE:\s*(\d+)", result)
    feedback_match = re.search(r"FEEDBACK:\s*(.+)", result)

    if score_match:
        score = int(score_match.group(1))
    if feedback_match:
        feedback = feedback_match.group(1).strip()

    if score < REFLECTION_PASS_SCORE and state["reflection_count"] < MAX_REFLECTIONS:
        improved_query = (
            state["enriched_query"]
            + f"\n\nYour previous answer was insufficient: {feedback}. Please be more specific."
        )
        return {
            "reflection_count": state["reflection_count"] + 1,
            "reflection_score": score,
            "enriched_query": improved_query,
        }

    return {
        "reflection_count": state["reflection_count"] + 1,
        "reflection_score": score,
    }


def route_after_input_guard(state: OrchestratorState) -> str:
    return "blocked" if state["blocked"] else "proceed"


def route_query(state: OrchestratorState) -> str:
    return state["query_type"]


def route_after_reflect(state: OrchestratorState) -> str:
    if (
        state["reflection_score"] < REFLECTION_PASS_SCORE
        and state["reflection_count"] <= MAX_REFLECTIONS
    ):
        return state["query_type"]
    return "save_memory"


def build_graph():
    graph = StateGraph(OrchestratorState)

    graph.add_node("input_guardrail", input_guardrail)
    graph.add_node("blocked_response", blocked_response)
    graph.add_node("load_memory", load_memory)
    graph.add_node("classify", classify_query)
    graph.add_node("code_analysis", call_agent)
    graph.add_node("impact_analysis", call_agent)
    graph.add_node("doc_generation", call_agent)
    graph.add_node("output_guardrail", output_guardrail)
    graph.add_node("reflect", reflect)
    graph.add_node("save_memory", save_memory)

    graph.set_entry_point("input_guardrail")

    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guard,
        {"blocked": "blocked_response", "proceed": "load_memory"},
    )

    graph.add_edge("blocked_response", END)
    graph.add_edge("load_memory", "classify")

    graph.add_conditional_edges(
        "classify",
        route_query,
        {
            "code_analysis": "code_analysis",
            "impact_analysis": "impact_analysis",
            "doc_generation": "doc_generation",
        },
    )

    graph.add_edge("code_analysis", "output_guardrail")
    graph.add_edge("impact_analysis", "output_guardrail")
    graph.add_edge("doc_generation", "output_guardrail")
    graph.add_edge("output_guardrail", "reflect")

    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {
            "code_analysis": "code_analysis",
            "impact_analysis": "impact_analysis",
            "doc_generation": "doc_generation",
            "save_memory": "save_memory",
        },
    )

    graph.add_edge("save_memory", END)

    return graph.compile()


orchestrator = build_graph()
