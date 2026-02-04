from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.storage.json_store import JsonStore
from app.storage.paths import data_dir


@dataclass
class ConsentRequest:
    id: str
    tool_name: str
    payload: Dict[str, Any]
    status: str
    created_at: str
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None


class ConsentStore:
    def __init__(self) -> None:
        self._store = JsonStore(data_dir() / "consent_requests.json")

    def _load(self) -> List[ConsentRequest]:
        data = self._store.read({"requests": []})
        return [ConsentRequest(**item) for item in data.get("requests", [])]

    def _save(self, items: List[ConsentRequest]) -> None:
        self._store.write({"requests": [asdict(item) for item in items]})

    def create(self, tool_name: str, payload: Dict[str, Any]) -> ConsentRequest:
        items = self._load()
        request = ConsentRequest(
            id=uuid4().hex,
            tool_name=tool_name,
            payload=payload,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        items.append(request)
        self._save(items)
        return request

    def list(self, *, status: Optional[str] = None) -> List[ConsentRequest]:
        items = self._load()
        if status:
            return [item for item in items if item.status == status]
        return items

    def resolve(self, request_id: str, *, approved: bool) -> Optional[ConsentRequest]:
        items = self._load()
        updated: Optional[ConsentRequest] = None
        for item in items:
            if item.id == request_id:
                item.status = "approved" if approved else "denied"
                item.resolved_at = datetime.now(timezone.utc).isoformat()
                item.resolution = "approved" if approved else "denied"
                updated = item
                break
        if updated:
            self._save(items)
        return updated


CONSENT_STORE = ConsentStore()
