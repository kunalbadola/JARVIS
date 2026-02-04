from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from app.storage.paths import data_dir


@dataclass
class AuditLogEntry:
    id: str
    event: str
    actor: str
    details: Dict[str, Any]
    created_at: str


class AuditLogger:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (data_dir() / "audit.log")
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: str, *, actor: str, details: Dict[str, Any]) -> AuditLogEntry:
        entry = AuditLogEntry(
            id=uuid4().hex,
            event=event,
            actor=actor,
            details=details,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.__dict__) + "\n")
        return entry

    def list_entries(self, *, limit: int = 100) -> List[AuditLogEntry]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        selected = lines[-limit:]
        entries: List[AuditLogEntry] = []
        for line in selected:
            if not line.strip():
                continue
            payload = json.loads(line)
            entries.append(
                AuditLogEntry(
                    id=payload.get("id", ""),
                    event=payload.get("event", ""),
                    actor=payload.get("actor", ""),
                    details=payload.get("details", {}),
                    created_at=payload.get("created_at", ""),
                )
            )
        return entries


AUDIT_LOGGER = AuditLogger()
