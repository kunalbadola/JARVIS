from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.llm.registry import get_provider
from app.tools.permissions import check_permission
from app.tools.registry import get_tool, list_tools


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    schema: Dict[str, Any]
    result: Dict[str, Any]


@dataclass
class AgentResponse:
    intent: str
    provider: str
    completion: Dict[str, Any]
    tool_calls: List[ToolCall]


def detect_intent(message: str) -> str:
    lowered = message.lower()
    if any(word in lowered for word in ["remember", "save", "note"]):
        return "remember"
    if any(word in lowered for word in ["summary", "summarize"]):
        return "store_summary"
    if any(word in lowered for word in ["task", "todo", "remind"]):
        return "create_task"
    if any(word in lowered for word in ["recall", "search", "lookup", "find memory"]):
        return "recall"
    if any(word in lowered for word in ["calendar", "schedule", "meeting", "appointment"]):
        return "calendar"
    if any(word in lowered for word in ["email", "mail", "inbox", "message"]):
        return "email"
    if any(word in lowered for word in ["home assistant", "smart home", "lights", "thermostat"]):
        return "smart_home"
    if any(word in lowered for word in ["run command", "execute", "terminal", "shell"]):
        return "system_command"
    return "general"


def select_tools(intent: str) -> List[str]:
    intent_map = {
        "remember": "remember",
        "create_task": "create_task",
        "store_summary": "store_summary",
        "recall": "recall",
        "calendar": "calendar_crud",
        "email": "email_message",
        "smart_home": "smart_home_control",
        "system_command": "system_command",
    }
    if intent in intent_map:
        return [intent_map[intent]]
    return []


def run_agent(message: str, provider_name: str) -> AgentResponse:
    intent = detect_intent(message)
    provider = get_provider(provider_name)
    completion = provider.generate(prompt=message, context={"intent": intent})

    tool_calls: List[ToolCall] = []
    for tool_name in select_tools(intent):
        tool = get_tool(tool_name)
        arguments = build_tool_arguments(tool_name, message)
        allowed, reason = check_permission(tool_name, arguments)
        if not allowed:
            result = {"status": "permission_required", "message": reason}
        else:
            result = tool.handler(arguments)
        tool_calls.append(
            ToolCall(
                name=tool.name,
                arguments=arguments,
                schema=tool.input_schema,
                result=result,
            )
        )

    return AgentResponse(
        intent=intent,
        provider=provider_name,
        completion=completion,
        tool_calls=tool_calls,
    )


def build_tool_arguments(tool_name: str, message: str) -> Dict[str, Any]:
    lowered = message.lower()
    if tool_name == "remember":
        return {"content": message}
    if tool_name == "store_summary":
        return {"content": message}
    if tool_name == "recall":
        return {"query": message}
    if tool_name == "create_task":
        return {"title": message}
    if tool_name == "calendar_crud":
        action = "list"
        if any(word in lowered for word in ["create", "schedule", "book"]):
            action = "create"
        elif any(word in lowered for word in ["update", "edit", "reschedule", "move"]):
            action = "update"
        elif any(word in lowered for word in ["delete", "cancel", "remove"]):
            action = "delete"
        return {"action": action, "request": message, "approved": False}
    if tool_name == "email_message":
        action = "search"
        if any(word in lowered for word in ["compose", "draft", "write"]):
            action = "compose"
        elif "send" in lowered:
            action = "send"
        return {"action": action, "request": message, "approved": False}
    if tool_name == "smart_home_control":
        service = None
        if "turn on" in lowered:
            service = "turn_on"
        elif "turn off" in lowered:
            service = "turn_off"
        elif "temperature" in lowered or "thermostat" in lowered:
            service = "set_temperature"
        return {"service": service, "request": message, "approved": False}
    if tool_name == "system_command":
        return {"command": "", "request": message, "approved": False}
    return {}


def available_tools_payload() -> List[Dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in list_tools()
    ]
