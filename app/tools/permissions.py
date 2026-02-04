from __future__ import annotations

from typing import Any, Dict, Tuple

SENSITIVE_TOOLS = {
    "calendar_crud",
    "email_message",
    "smart_home_control",
    "system_command",
}


def check_permission(tool_name: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    if tool_name not in SENSITIVE_TOOLS:
        return True, ""
    approved = payload.get("approved")
    if approved is True:
        return True, ""
    return False, f"Permission required to run {tool_name}."
