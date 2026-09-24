import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from core.models import AgentCard, TaskRequest, TaskResponse
from core.vectorstore import VectorStore
from core.graph_store import GraphStore
from core.ollama_client import embed, llm

EXTRACT_PROMPT = (
    "Extract the function or module name being asked about.\n"
    "Reply with only the name, nothing else.\n"
    "Query: {query}"
)

app = FastAPI(title="Impact Analyzer Agent")

AGENT_CARD = AgentCard(
    name="Impact Analyzer",
    description="Analyzes what breaks if a function changes using knowledge graph traversal",
    url="http://localhost:8002",
    capabilities=["impact_analysis", "graph_traversal", "dependency_analysis"],
)


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD.model_dump()


@app.post("/tasks", response_model=TaskResponse)
async def run_task(request: TaskRequest):
    try:
        graph = GraphStore()
        loaded = graph.load()

        # Extract function name from query
        extract_prompt = EXTRACT_PROMPT.format(query=request.query)
        function_name = llm(extract_prompt).strip().strip('"').strip("'")

        callers = graph.find_callers(function_name) if loaded else []
        callees = graph.find_callees(function_name) if loaded else []

        # Supplement with semantic context
        store = VectorStore()
        results = store.query(embed(request.query), n_results=3)
        context = "\n\n---\n\n".join([r["document"] for r in results])
        chroma_sources = [r["metadata"]["name"] for r in results]

        # Use graph sources if found, fall back to ChromaDB sources
        sources = [n.name for n in callers + callees] or chroma_sources

        prompt = f"""You are a code impact analysis assistant.

Function being analyzed: {function_name}

Functions that CALL {function_name} (affected if it changes):
{[n.name for n in callers] or "None found"}

Functions that {function_name} CALLS (its dependencies):
{[n.name for n in callees] or "None found"}

Additional code context:
{context}

Question: {request.query}

Explain the impact clearly."""

        answer = llm(prompt)
        return TaskResponse(task_id=request.task_id, status="completed", result=answer, sources=sources)

    except Exception as e:
        return TaskResponse(task_id=request.task_id, status="failed", result=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "impact_analyzer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
