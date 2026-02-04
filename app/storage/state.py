from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TaskItem:
    id: int
    title: str
    status: str = "open"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryItem:
    id: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class InMemoryState:
    def __init__(self) -> None:
        self._tasks: List[TaskItem] = []
        self._memory: List[MemoryItem] = []
        self._task_id = 0
        self._memory_id = 0

    def list_tasks(self) -> List[TaskItem]:
        return list(self._tasks)

    def add_task(self, title: str, status: str = "open", metadata: Dict[str, Any] | None = None) -> TaskItem:
        self._task_id += 1
        item = TaskItem(id=self._task_id, title=title, status=status, metadata=metadata or {})
        self._tasks.append(item)
        return item

    def list_memory(self) -> List[MemoryItem]:
        return list(self._memory)

    def add_memory(self, content: str, metadata: Dict[str, Any] | None = None) -> MemoryItem:
        self._memory_id += 1
        item = MemoryItem(id=self._memory_id, content=content, metadata=metadata or {})
        self._memory.append(item)
        return item


STATE = InMemoryState()
