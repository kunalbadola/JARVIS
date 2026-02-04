from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JsonStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def read(self, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self._path.exists():
            return default or {}
        payload = self._path.read_text(encoding="utf-8").strip()
        if not payload:
            return default or {}
        return json.loads(payload)

    def write(self, payload: Dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
