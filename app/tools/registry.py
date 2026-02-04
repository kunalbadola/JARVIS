from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from app.storage.state import STATE

ToolHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolHandler


TOOLS: Dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    TOOLS[tool.name] = tool


def list_tools() -> List[Tool]:
    return list(TOOLS.values())


def get_tool(name: str) -> Tool:
    return TOOLS[name]


def _remember_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    content = payload.get("content", "")
    item = STATE.add_memory(content=content, metadata=payload.get("metadata"))
    return {"memory_id": item.id, "content": item.content}


def _create_task_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    title = payload.get("title", "Untitled task")
    status = payload.get("status", "open")
    item = STATE.add_task(title=title, status=status, metadata=payload.get("metadata"))
    return {"task_id": item.id, "title": item.title, "status": item.status}


register_tool(
    Tool(
        name="remember",
        description="Store a memory snippet for later retrieval.",
        input_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["content"],
        },
        handler=_remember_tool,
    )
)

register_tool(
    Tool(
        name="create_task",
        description="Create a new task for the agent to track.",
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "status": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["title"],
        },
        handler=_create_task_tool,
    )
)
