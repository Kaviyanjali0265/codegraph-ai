import os
import uuid
import httpx
from core.models import TaskRequest, TaskResponse

TIMEOUT = 300.0

AGENT_URLS = {
    "code_analysis": os.getenv("CODE_ANALYST_URL", "http://localhost:8001"),
    "impact_analysis": os.getenv("IMPACT_ANALYZER_URL", "http://localhost:8002"),
    "doc_generation": os.getenv("DOC_GENERATOR_URL", "http://localhost:8003"),
}


class AgentClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_card(self) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/.well-known/agent.json")
            response.raise_for_status()
            return response.json()

    def call(self, query: str) -> TaskResponse:
        task = TaskRequest(
            task_id=str(uuid.uuid4()),
            query=query,
        )
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{self.base_url}/tasks",
                json=task.model_dump(),
            )
            response.raise_for_status()
            return TaskResponse(**response.json())


def get_client(query_type: str) -> AgentClient:
    url = AGENT_URLS[query_type]
    return AgentClient(url)
