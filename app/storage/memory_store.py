from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

DEFAULT_COLLECTION = "agent_memories"
DEFAULT_EMBEDDING_DIM = 256


@dataclass
class MemoryRecord:
    id: str
    content: str
    metadata: Dict[str, Any]
    created_at: str


def _normalize(vector: List[float]) -> List[float]:
    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_text(text: str, dimensions: int = DEFAULT_EMBEDDING_DIM) -> List[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"\w+", text.lower()):
        digest = blake2b(token.encode("utf-8"), digest_size=4).digest()
        idx = int.from_bytes(digest, "little") % dimensions
        vector[idx] += 1.0
    return _normalize(vector)


class VectorMemoryStore:
    def __init__(
        self,
        *,
        path: Optional[str] = None,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
    ) -> None:
        storage_path = path or os.getenv("VECTOR_DB_PATH", ":memory:")
        self._client = QdrantClient(path=storage_path)
        self._collection = collection_name
        self._embedding_dim = embedding_dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            self._client.get_collection(self._collection)
        except Exception:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qdrant_models.VectorParams(
                    size=self._embedding_dim,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def _record_to_payload(self, record: MemoryRecord) -> Dict[str, Any]:
        return {
            "content": record.content,
            "metadata": record.metadata,
            "created_at": record.created_at,
        }

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        memory_type: str = "note",
    ) -> MemoryRecord:
        record_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "type": memory_type,
            **(metadata or {}),
        }
        record = MemoryRecord(
            id=record_id,
            content=content,
            metadata=payload,
            created_at=timestamp,
        )
        vector = embed_text(content, self._embedding_dim)
        self._client.upsert(
            collection_name=self._collection,
            points=[
                qdrant_models.PointStruct(
                    id=record_id,
                    vector=vector,
                    payload=self._record_to_payload(record),
                )
            ],
        )
        return record

    def index_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        document_type: str = "document",
    ) -> MemoryRecord:
        return self.add_memory(
            content=content,
            metadata=metadata,
            memory_type=document_type,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        vector = embed_text(query, self._embedding_dim)
        query_filter = None
        if memory_type:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_models.MatchValue(value=memory_type),
                    )
                ]
            )
        results = self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter,
        )
        return [
            {
                "id": point.id,
                "score": point.score,
                "content": point.payload.get("content"),
                "metadata": point.payload.get("metadata", {}),
                "created_at": point.payload.get("created_at"),
            }
            for point in results
        ]

    def list_memory(self, *, limit: int = 100) -> List[MemoryRecord]:
        records: List[MemoryRecord] = []
        next_offset = None
        while True:
            points, next_offset = self._client.scroll(
                collection_name=self._collection,
                limit=limit,
                offset=next_offset,
                with_payload=True,
            )
            for point in points:
                payload = point.payload or {}
                records.append(
                    MemoryRecord(
                        id=str(point.id),
                        content=payload.get("content", ""),
                        metadata=payload.get("metadata", {}),
                        created_at=payload.get("created_at", ""),
                    )
                )
            if next_offset is None:
                break
        return records

    def forget(
        self,
        *,
        ids: Optional[Iterable[str]] = None,
        memory_type: Optional[str] = None,
        tag: Optional[str] = None,
        before: Optional[datetime] = None,
        purge_all: bool = False,
    ) -> int:
        if purge_all:
            self._client.delete_collection(self._collection)
            self._ensure_collection()
            return 0
        must_conditions: List[qdrant_models.FieldCondition] = []
        if memory_type:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="metadata.type",
                    match=qdrant_models.MatchValue(value=memory_type),
                )
            )
        if tag:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="metadata.tags",
                    match=qdrant_models.MatchValue(value=tag),
                )
            )
        if before:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="created_at",
                    range=qdrant_models.Range(lt=before.isoformat()),
                )
            )
        points_selector: qdrant_models.PointsSelector
        if ids:
            points_selector = qdrant_models.PointIdsList(points=list(ids))
        elif must_conditions:
            points_selector = qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(must=must_conditions)
            )
        else:
            return 0
        self._client.delete(
            collection_name=self._collection,
            points_selector=points_selector,
        )
        return 0

    def export(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": record.id,
                "content": record.content,
                "metadata": record.metadata,
                "created_at": record.created_at,
            }
            for record in self.list_memory()
        ]


def memory_store_from_env() -> VectorMemoryStore:
    return VectorMemoryStore(
        path=os.getenv("VECTOR_DB_PATH"),
        collection_name=os.getenv("VECTOR_DB_COLLECTION", DEFAULT_COLLECTION),
        embedding_dim=int(os.getenv("VECTOR_DB_DIM", DEFAULT_EMBEDDING_DIM)),
    )
