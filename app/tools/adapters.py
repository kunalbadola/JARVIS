from __future__ import annotations

import os
import shlex
import subprocess
import time
from typing import Any, Dict, List


class CalendarAdapter:
    def __init__(self) -> None:
        self._events: Dict[str, Dict[str, Any]] = {}

    def _is_configured(self, provider: str) -> bool:
        if provider == "google":
            return bool(os.getenv("GOOGLE_CALENDAR_TOKEN"))
        if provider == "outlook":
            return bool(os.getenv("OUTLOOK_CALENDAR_TOKEN"))
        return False

    def handle(self, provider: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if provider not in {"google", "outlook"}:
            return {"status": "error", "message": f"Unsupported provider: {provider}"}
        if not self._is_configured(provider):
            return {
                "status": "not_configured",
                "message": f"{provider} calendar is not configured.",
            }
        if action == "create":
            event_id = f"evt_{int(time.time() * 1000)}"
            event = {
                "id": event_id,
                "title": payload.get("title", "Untitled event"),
                "start": payload.get("start"),
                "end": payload.get("end"),
                "attendees": payload.get("attendees", []),
                "location": payload.get("location"),
            }
            self._events[event_id] = event
            return {"status": "created", "provider": provider, "event": event}
        if action == "update":
            event_id = payload.get("event_id")
            if not event_id or event_id not in self._events:
                return {"status": "error", "message": "Event not found."}
            event = self._events[event_id]
            event.update({k: v for k, v in payload.items() if k in event and v is not None})
            return {"status": "updated", "provider": provider, "event": event}
        if action == "delete":
            event_id = payload.get("event_id")
            if not event_id or event_id not in self._events:
                return {"status": "error", "message": "Event not found."}
            event = self._events.pop(event_id)
            return {"status": "deleted", "provider": provider, "event": event}
        if action in {"list", "read"}:
            return {
                "status": "ok",
                "provider": provider,
                "events": list(self._events.values()),
            }
        return {"status": "error", "message": f"Unknown action: {action}"}


class EmailAdapter:
    def __init__(self) -> None:
        self._drafts: Dict[str, Dict[str, Any]] = {}
        self._messages: Dict[str, Dict[str, Any]] = {}

    def _is_configured(self, provider: str) -> bool:
        if provider == "google":
            return bool(os.getenv("GOOGLE_EMAIL_TOKEN"))
        if provider == "outlook":
            return bool(os.getenv("OUTLOOK_EMAIL_TOKEN"))
        return False

    def handle(self, provider: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if provider not in {"google", "outlook"}:
            return {"status": "error", "message": f"Unsupported provider: {provider}"}
        if not self._is_configured(provider):
            return {
                "status": "not_configured",
                "message": f"{provider} email is not configured.",
            }
        if action == "search":
            query = payload.get("query", "")
            matches = [
                message for message in self._messages.values() if query.lower() in message.get("subject", "").lower()
            ]
            return {"status": "ok", "provider": provider, "results": matches}
        if action == "compose":
            draft_id = f"draft_{int(time.time() * 1000)}"
            draft = {
                "id": draft_id,
                "to": payload.get("to", []),
                "subject": payload.get("subject", ""),
                "body": payload.get("body", ""),
                "cc": payload.get("cc", []),
                "bcc": payload.get("bcc", []),
            }
            self._drafts[draft_id] = draft
            return {"status": "drafted", "provider": provider, "draft": draft}
        if action == "send":
            draft_id = payload.get("draft_id")
            if draft_id:
                draft = self._drafts.get(draft_id)
                if not draft:
                    return {"status": "error", "message": "Draft not found."}
                message = draft
            else:
                message = {
                    "to": payload.get("to", []),
                    "subject": payload.get("subject", ""),
                    "body": payload.get("body", ""),
                    "cc": payload.get("cc", []),
                    "bcc": payload.get("bcc", []),
                }
            message_id = f"msg_{int(time.time() * 1000)}"
            message["id"] = message_id
            self._messages[message_id] = message
            return {"status": "sent", "provider": provider, "message": message}
        return {"status": "error", "message": f"Unknown action: {action}"}


class HomeAssistantAdapter:
    def _is_configured(self) -> bool:
        return bool(os.getenv("HOME_ASSISTANT_URL") and os.getenv("HOME_ASSISTANT_TOKEN"))

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._is_configured():
            return {
                "status": "not_configured",
                "message": "Home Assistant is not configured.",
            }
        return {
            "status": "queued",
            "service": payload.get("service"),
            "entity_id": payload.get("entity_id"),
            "device_id": payload.get("device_id"),
            "data": payload.get("data", {}),
        }


class SafeCommandRunner:
    SAFE_COMMANDS: Dict[str, List[str]] = {
        "date": [],
        "whoami": [],
        "uptime": [],
        "pwd": [],
        "ls": ["-a", "-l", "-la", "-al"],
    }

    def _parse_command(self, payload: Dict[str, Any]) -> List[str]:
        if isinstance(payload.get("command"), list):
            return [str(part) for part in payload.get("command", [])]
        if isinstance(payload.get("command"), str):
            return shlex.split(payload.get("command", ""))
        return []

    def _is_allowed(self, command: List[str]) -> tuple[bool, str]:
        if not command:
            return False, "No command provided."
        base = command[0]
        if base not in self.SAFE_COMMANDS:
            return False, f"Command '{base}' is not in the allowlist."
        allowed_args = set(self.SAFE_COMMANDS[base])
        provided_args = set(command[1:])
        if allowed_args and not provided_args.issubset(allowed_args):
            return False, "Command arguments are not allowlisted."
        if not allowed_args and provided_args:
            return False, "Command does not accept arguments."
        return True, ""

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        command = self._parse_command(payload)
        allowed, reason = self._is_allowed(command)
        if not allowed:
            return {"status": "denied", "message": reason}
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {
            "status": "ok",
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
