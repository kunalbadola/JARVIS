from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict

from app.storage.json_store import JsonStore
from app.storage.paths import data_dir


@dataclass
class PrivacySettings:
    retention_days: int = 30
    data_export_enabled: bool = True
    delete_on_request: bool = True


class PrivacyStore:
    def __init__(self) -> None:
        self._store = JsonStore(data_dir() / "privacy_settings.json")

    def load(self) -> PrivacySettings:
        payload = self._store.read({})
        if not payload:
            return PrivacySettings()
        return PrivacySettings(
            retention_days=int(payload.get("retention_days", 30)),
            data_export_enabled=bool(payload.get("data_export_enabled", True)),
            delete_on_request=bool(payload.get("delete_on_request", True)),
        )

    def save(self, settings: PrivacySettings) -> PrivacySettings:
        self._store.write(asdict(settings))
        return settings


PRIVACY_STORE = PrivacyStore()
