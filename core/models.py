from pydantic import BaseModel, Field
from typing import Literal


class CodeChunk(BaseModel):
    id: str
    file: str
    name: str
    type: Literal["function", "class", "method"]
    code: str
    docstring: str = ""
    lineno: int
    calls: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    name: str
    type: Literal["function", "class", "method", "file"]
    file: str
    lineno: int = 0


class QueryRequest(BaseModel):
    query: str
    session_id: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    agent_used: str = ""


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    capabilities: list[str]


class TaskRequest(BaseModel):
    task_id: str
    query: str


class TaskResponse(BaseModel):
    task_id: str
    status: Literal["completed", "failed"]
    result: str
    sources: list[str] = Field(default_factory=list)
