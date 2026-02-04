from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.storage.encrypted_store import EncryptedJsonStore
from app.storage.paths import data_dir


@dataclass
class SecretRecord:
    key: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


class SecretsManager:
    def __init__(self) -> None:
        self._store = EncryptedJsonStore(data_dir() / "secrets.enc")

    def _load(self) -> Dict[str, Dict[str, Any]]:
        return self._store.read({"secrets": {}}).get("secrets", {})

    def _save(self, secrets: Dict[str, Dict[str, Any]]) -> None:
        self._store.write({"secrets": secrets})

    def set_secret(self, key: str, value: str, *, metadata: Optional[Dict[str, Any]] = None) -> SecretRecord:
        secrets = self._load()
        now = datetime.now(timezone.utc).isoformat()
        record = secrets.get(key, {})
        created_at = record.get("created_at", now)
        secrets[key] = {
            "value": value,
            "created_at": created_at,
            "updated_at": now,
            "metadata": metadata or {},
        }
        self._save(secrets)
        return SecretRecord(key=key, created_at=created_at, updated_at=now, metadata=metadata or {})

    def get_secret(self, key: str) -> Optional[str]:
        secrets = self._load()
        record = secrets.get(key)
        if not record:
            return None
        return record.get("value")

    def delete_secret(self, key: str) -> bool:
        secrets = self._load()
        if key not in secrets:
            return False
        del secrets[key]
        self._save(secrets)
        return True

    def list_secrets(self) -> List[SecretRecord]:
        secrets = self._load()
        records: List[SecretRecord] = []
        for key, record in secrets.items():
            records.append(
                SecretRecord(
                    key=key,
                    created_at=record.get("created_at", ""),
                    updated_at=record.get("updated_at", ""),
                    metadata=record.get("metadata", {}),
                )
            )
        return records


SECRETS_MANAGER = SecretsManager()
