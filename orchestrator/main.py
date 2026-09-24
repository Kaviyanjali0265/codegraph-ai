import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from core.auth import User, get_current_user
from core.models import QueryRequest, QueryResponse
from orchestrator.graph import orchestrator

app = FastAPI(title="CodeGraph AI — Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _initial_state(request: QueryRequest, user: User) -> dict:
    return {
        "query": request.query,
        "session_id": request.session_id or user.user_id,
        "enriched_query": "",
        "query_type": "",
        "agent_result": "",
        "sources": [],
        "blocked": False,
        "block_reason": "",
        "reflection_count": 0,
        "reflection_score": 0,
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, user: User = Depends(get_current_user)):
    """Standard endpoint — waits for full answer then returns."""
    result = orchestrator.invoke(_initial_state(request, user))
    return QueryResponse(
        answer=result["agent_result"],
        sources=result["sources"],
        agent_used=result["query_type"],
    )


@app.post("/query/stream")
async def query_stream(request: QueryRequest, user: User = Depends(get_current_user)):
    """Streaming endpoint — sends SSE events as each graph node completes.
    Final 'done' event includes the complete answer, sources, and agent used.
    Uses fetch() streaming on the client side (EventSource can't POST or send headers).
    """

    def generate():
        latest_result = ""
        latest_sources: list = []
        latest_agent = ""

        for event in orchestrator.stream(_initial_state(request, user)):
            node_name = list(event.keys())[0]
            state_update = event[node_name]
            chunk: dict = {"node": node_name}

            if node_name == "classify":
                latest_agent = state_update.get("query_type", "")
                chunk["query_type"] = latest_agent

            elif node_name in ("code_analysis", "impact_analysis", "doc_generation"):
                latest_result = state_update.get("agent_result", latest_result)
                latest_sources = state_update.get("sources", latest_sources)
                chunk["status"] = "agent_done"

            elif node_name == "output_guardrail":
                if state_update.get("blocked"):
                    latest_result = state_update.get("agent_result", latest_result)

            elif node_name == "reflect":
                chunk["reflection_score"] = state_update.get("reflection_score", 0)
                chunk["reflection_count"] = state_update.get("reflection_count", 0)

            elif node_name == "blocked_response":
                latest_result = state_update.get("agent_result", "")
                chunk["blocked"] = True
                chunk["reason"] = state_update.get("block_reason", "")

            yield f"data: {json.dumps(chunk)}\n\n"

        yield f"data: {json.dumps({'node': 'done', 'result': latest_result, 'sources': latest_sources, 'agent_used': latest_agent})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/evals/results")
async def evals_results():
    """Return the latest saved eval results for the dashboard."""
    results_path = Path(__file__).parent.parent / "evals" / "results.json"
    if not results_path.exists():
        return JSONResponse({"error": "No eval results found. Run: python evals/run_evals.py --json --skip-generation"}, status_code=404)
    with open(results_path) as f:
        return JSONResponse(json.load(f))


@app.get("/health")
async def health():
    return {"status": "ok"}


# Mount frontend — must be last so API routes take priority
_FRONTEND = Path(__file__).parent.parent / "frontend"
if _FRONTEND.exists():
    app.mount("/ui", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
