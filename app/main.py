from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent.router import AgentResponse, available_tools_payload, run_agent
from app.storage.state import STATE, MemoryItem, TaskItem

app = FastAPI(title="JARVIS Backend", version="0.1.0")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    provider: str = Field("local", description="LLM provider: openai | anthropic | local")


class ToolCallResponse(BaseModel):
    name: str
    arguments: Dict[str, Any]
    schema: Dict[str, Any]
    result: Dict[str, Any]


class ChatResponse(BaseModel):
    intent: str
    provider: str
    completion: Dict[str, Any]
    tool_calls: List[ToolCallResponse]
    available_tools: List[Dict[str, Any]]


class VoiceRequest(BaseModel):
    transcript: str
    provider: str = "local"


class TaskCreateRequest(BaseModel):
    title: str
    status: str = "open"
    metadata: Optional[Dict[str, Any]] = None


class MemoryCreateRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    status: str
    metadata: Dict[str, Any]


class MemoryResponse(BaseModel):
    id: int
    content: str
    metadata: Dict[str, Any]


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    response: AgentResponse = run_agent(request.message, request.provider)
    return ChatResponse(
        intent=response.intent,
        provider=response.provider,
        completion=response.completion,
        tool_calls=[
            ToolCallResponse(
                name=call.name,
                arguments=call.arguments,
                schema=call.schema,
                result=call.result,
            )
            for call in response.tool_calls
        ],
        available_tools=available_tools_payload(),
    )


@app.post("/voice", response_model=ChatResponse)
async def voice(request: VoiceRequest) -> ChatResponse:
    response: AgentResponse = run_agent(request.transcript, request.provider)
    return ChatResponse(
        intent=response.intent,
        provider=response.provider,
        completion=response.completion,
        tool_calls=[
            ToolCallResponse(
                name=call.name,
                arguments=call.arguments,
                schema=call.schema,
                result=call.result,
            )
            for call in response.tool_calls
        ],
        available_tools=available_tools_payload(),
    )


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks() -> List[TaskResponse]:
    return [
        TaskResponse(id=item.id, title=item.title, status=item.status, metadata=item.metadata)
        for item in STATE.list_tasks()
    ]


@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest) -> TaskResponse:
    item: TaskItem = STATE.add_task(title=request.title, status=request.status, metadata=request.metadata)
    return TaskResponse(id=item.id, title=item.title, status=item.status, metadata=item.metadata)


@app.get("/memory", response_model=List[MemoryResponse])
async def list_memory() -> List[MemoryResponse]:
    return [
        MemoryResponse(id=item.id, content=item.content, metadata=item.metadata)
        for item in STATE.list_memory()
    ]


@app.post("/memory", response_model=MemoryResponse)
async def create_memory(request: MemoryCreateRequest) -> MemoryResponse:
    item: MemoryItem = STATE.add_memory(content=request.content, metadata=request.metadata)
    return MemoryResponse(id=item.id, content=item.content, metadata=item.metadata)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok"}
