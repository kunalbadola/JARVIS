from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

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


def _store_summary_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    content = payload.get("content", "")
    item = STATE.add_summary(content=content, metadata=payload.get("metadata"))
    return {"summary_id": item.id, "content": item.content}


def _index_document_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    content = payload.get("content", "")
    metadata = payload.get("metadata")
    item = STATE.index_document(content=content, metadata=metadata)
    return {"document_id": item.id, "content": item.content}


def _recall_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = payload.get("query", "")
    limit = payload.get("limit", 5)
    memory_type = payload.get("memory_type")
    results = STATE.search_memory(query, limit=limit, memory_type=memory_type)
    return {"matches": results}


def _forget_memory_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    ids = payload.get("ids")
    memory_type = payload.get("memory_type")
    tag = payload.get("tag")
    before = payload.get("before")
    purge_all = payload.get("purge_all", False)
    before_dt: Optional[datetime] = None
    if before:
        before_dt = datetime.fromisoformat(before)
    STATE.forget_memory(
        ids=ids,
        memory_type=memory_type,
        tag=tag,
        before=before_dt,
        purge_all=purge_all,
    )
    return {"status": "ok"}


def _export_memory_tool(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"memories": STATE.export_memory()}


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
        name="store_summary",
        description="Store a conversation summary for long-term recall.",
        input_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["content"],
        },
        handler=_store_summary_tool,
    )
)

register_tool(
    Tool(
        name="index_document",
        description="Index a document into vector memory for search.",
        input_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["content"],
        },
        handler=_index_document_tool,
    )
)

register_tool(
    Tool(
        name="recall",
        description="Retrieve relevant memories by semantic search.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                "memory_type": {"type": "string"},
            },
            "required": ["query"],
        },
        handler=_recall_tool,
    )
)

register_tool(
    Tool(
        name="forget_memory",
        description="Remove memories by id, type, tag, or timestamp.",
        input_schema={
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "string"}},
                "memory_type": {"type": "string"},
                "tag": {"type": "string"},
                "before": {"type": "string", "description": "ISO-8601 timestamp"},
                "purge_all": {"type": "boolean"},
            },
        },
        handler=_forget_memory_tool,
    )
)

register_tool(
    Tool(
        name="export_memory",
        description="Export all stored memories and metadata.",
        input_schema={"type": "object", "properties": {}},
        handler=_export_memory_tool,
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
