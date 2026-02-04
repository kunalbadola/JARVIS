from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.storage.memory_store import MemoryRecord, memory_store_from_env


@dataclass
class TaskItem:
    id: int
    title: str
    status: str = "open"
    metadata: Dict[str, Any] = field(default_factory=dict)


class InMemoryState:
    def __init__(self) -> None:
        self._tasks: List[TaskItem] = []
        self._task_id = 0
        self._memory_store = memory_store_from_env()

    def list_tasks(self) -> List[TaskItem]:
        return list(self._tasks)

    def add_task(self, title: str, status: str = "open", metadata: Dict[str, Any] | None = None) -> TaskItem:
        self._task_id += 1
        item = TaskItem(id=self._task_id, title=title, status=status, metadata=metadata or {})
        self._tasks.append(item)
        return item

    def list_memory(self) -> List[MemoryRecord]:
        return self._memory_store.list_memory()

    def add_memory(self, content: str, metadata: Dict[str, Any] | None = None) -> MemoryRecord:
        return self._memory_store.add_memory(content=content, metadata=metadata)

    def add_summary(self, content: str, metadata: Dict[str, Any] | None = None) -> MemoryRecord:
        return self._memory_store.add_memory(
            content=content,
            metadata=metadata,
            memory_type="summary",
        )

    def index_document(self, content: str, metadata: Dict[str, Any] | None = None) -> MemoryRecord:
        return self._memory_store.index_document(content=content, metadata=metadata)

    def search_memory(
        self, query: str, *, limit: int = 5, memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self._memory_store.search(query, limit=limit, memory_type=memory_type)

    def forget_memory(
        self,
        *,
        ids: Optional[List[str]] = None,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        before: Optional[datetime] = None,
        purge_all: bool = False,
    ) -> int:
        return self._memory_store.forget(
            ids=ids,
            memory_type=memory_type,
            tag=tag,
            before=before,
            purge_all=purge_all,
        )

    def export_memory(self) -> List[Dict[str, Any]]:
        return self._memory_store.export()


STATE = InMemoryState()
