from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.llm.registry import get_provider
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
    return "general"


def select_tools(intent: str) -> List[str]:
    if intent in {"remember", "create_task", "store_summary", "recall"}:
        return [intent]
    return []


def run_agent(message: str, provider_name: str) -> AgentResponse:
    intent = detect_intent(message)
    provider = get_provider(provider_name)
    completion = provider.generate(prompt=message, context={"intent": intent})

    tool_calls: List[ToolCall] = []
    for tool_name in select_tools(intent):
        tool = get_tool(tool_name)
        if tool_name == "remember":
            arguments = {"content": message}
        elif tool_name == "store_summary":
            arguments = {"content": message}
        elif tool_name == "recall":
            arguments = {"query": message}
        else:
            arguments = {"title": message}
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


def available_tools_payload() -> List[Dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in list_tools()
    ]
