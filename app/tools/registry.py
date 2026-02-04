from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.storage.state import STATE
from app.tools.adapters import CalendarAdapter, EmailAdapter, HomeAssistantAdapter, SafeCommandRunner
from app.tools.permissions import check_permission

ToolHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolHandler


TOOLS: Dict[str, Tool] = {}
_CALENDAR_ADAPTER = CalendarAdapter()
_EMAIL_ADAPTER = EmailAdapter()
_HOME_ASSISTANT_ADAPTER = HomeAssistantAdapter()
_COMMAND_RUNNER = SafeCommandRunner()


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


def _calendar_crud_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_permission("calendar_crud", payload)
    if not allowed:
        return {"status": "permission_required", "message": reason}
    provider = payload.get("provider", "google")
    action = payload.get("action", "list")
    return _CALENDAR_ADAPTER.handle(provider, action, payload)


def _email_message_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_permission("email_message", payload)
    if not allowed:
        return {"status": "permission_required", "message": reason}
    provider = payload.get("provider", "google")
    action = payload.get("action", "search")
    return _EMAIL_ADAPTER.handle(provider, action, payload)


def _smart_home_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_permission("smart_home_control", payload)
    if not allowed:
        return {"status": "permission_required", "message": reason}
    return _HOME_ASSISTANT_ADAPTER.handle(payload)


def _system_command_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_permission("system_command", payload)
    if not allowed:
        return {"status": "permission_required", "message": reason}
    return _COMMAND_RUNNER.run(payload)


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

register_tool(
    Tool(
        name="calendar_crud",
        description="Create, read, update, or delete calendar events for Google or Outlook.",
        input_schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string", "enum": ["google", "outlook"]},
                "action": {"type": "string", "enum": ["create", "read", "update", "delete", "list"]},
                "title": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string"},
                "event_id": {"type": "string"},
                "approved": {"type": "boolean"},
            },
        },
        handler=_calendar_crud_tool,
    )
)

register_tool(
    Tool(
        name="email_message",
        description="Search, compose, or send emails using Google or Outlook.",
        input_schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string", "enum": ["google", "outlook"]},
                "action": {"type": "string", "enum": ["search", "compose", "send"]},
                "query": {"type": "string"},
                "to": {"type": "array", "items": {"type": "string"}},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "cc": {"type": "array", "items": {"type": "string"}},
                "bcc": {"type": "array", "items": {"type": "string"}},
                "draft_id": {"type": "string"},
                "approved": {"type": "boolean"},
            },
        },
        handler=_email_message_tool,
    )
)

register_tool(
    Tool(
        name="smart_home_control",
        description="Control Home Assistant devices and services.",
        input_schema={
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "entity_id": {"type": "string"},
                "device_id": {"type": "string"},
                "data": {"type": "object"},
                "approved": {"type": "boolean"},
            },
        },
        handler=_smart_home_tool,
    )
)

register_tool(
    Tool(
        name="system_command",
        description="Run a safe, allowlisted system command.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": ["string", "array"], "items": {"type": "string"}},
                "approved": {"type": "boolean"},
            },
            "required": ["command"],
        },
        handler=_system_command_tool,
    )
)
