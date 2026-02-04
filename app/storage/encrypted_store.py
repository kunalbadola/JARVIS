from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict

from cryptography.fernet import Fernet

from app.storage.paths import data_dir


def _load_key_from_env() -> bytes | None:
    raw = os.getenv("SECRETS_ENCRYPTION_KEY")
    if not raw:
        return None
    try:
        return base64.urlsafe_b64decode(raw)
    except Exception:
        return raw.encode("utf-8")


def _load_or_create_key_file(path: Path) -> bytes:
    if path.exists():
        return path.read_bytes().strip()
    key = Fernet.generate_key()
    path.write_bytes(key)
    os.chmod(path, 0o600)
    return key


def load_encryption_key() -> bytes:
    key = _load_key_from_env()
    if key:
        return base64.urlsafe_b64encode(key) if len(key) != 44 else key
    key_path = data_dir() / "secrets.key"
    return _load_or_create_key_file(key_path)


class EncryptedJsonStore:
    def __init__(self, path: Path, *, key: bytes | None = None) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(key or load_encryption_key())

    def read(self, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self._path.exists():
            return default or {}
        payload = self._path.read_bytes().strip()
        if not payload:
            return default or {}
        decrypted = self._fernet.decrypt(payload)
        return json.loads(decrypted.decode("utf-8"))

    def write(self, payload: Dict[str, Any]) -> None:
        serialized = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        encrypted = self._fernet.encrypt(serialized)
        self._path.write_bytes(encrypted)
        os.chmod(self._path, 0o600)
