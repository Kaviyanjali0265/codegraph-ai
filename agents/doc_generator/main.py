import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from core.models import AgentCard, TaskRequest, TaskResponse
from core.vectorstore import VectorStore
from core.ollama_client import embed, llm

app = FastAPI(title="Doc Generator Agent")

AGENT_CARD = AgentCard(
    name="Doc Generator",
    description="Generates professional markdown documentation for functions and modules",
    url="http://localhost:8003",
    capabilities=["doc_generation", "markdown_output"],
)


@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD.model_dump()


@app.post("/tasks", response_model=TaskResponse)
async def run_task(request: TaskRequest):
    try:
        store = VectorStore()
        results = store.query(embed(request.query), n_results=3)

        context = "\n\n---\n\n".join([r["document"] for r in results])
        sources = [r["metadata"]["name"] for r in results]

        prompt = f"""You are a technical documentation writer. Generate clear, professional documentation.

Code context:
{context}

Request: {request.query}

Write documentation in markdown with: description, parameters, returns, example usage."""

        answer = llm(prompt)
        return TaskResponse(task_id=request.task_id, status="completed", result=answer, sources=sources)

    except Exception as e:
        return TaskResponse(task_id=request.task_id, status="failed", result=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "doc_generator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
