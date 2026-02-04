from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List
from urllib.parse import urlencode
from uuid import uuid4

from app.storage.json_store import JsonStore
from app.storage.paths import data_dir


@dataclass
class IntegrationProvider:
    name: str
    label: str
    auth_url: str
    token_url: str
    client_id: str
    scopes: List[str]


PROVIDERS: Dict[str, IntegrationProvider] = {
    "google": IntegrationProvider(
        name="google",
        label="Google",
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        client_id="google-client-id",
        scopes=["calendar", "email"],
    ),
    "outlook": IntegrationProvider(
        name="outlook",
        label="Microsoft Outlook",
        auth_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        client_id="outlook-client-id",
        scopes=["calendars.readwrite", "mail.send"],
    ),
    "home_assistant": IntegrationProvider(
        name="home_assistant",
        label="Home Assistant",
        auth_url="https://my.home-assistant.io/redirect/oauth",
        token_url="https://my.home-assistant.io/redirect/oauth/token",
        client_id="home-assistant-client-id",
        scopes=["read", "write"],
    ),
}


class OAuthStateStore:
    def __init__(self) -> None:
        self._store = JsonStore(data_dir() / "oauth_state.json")

    def create(self, provider: str, redirect_uri: str) -> str:
        state = uuid4().hex
        payload = self._store.read({"states": {}})
        payload.setdefault("states", {})[state] = {
            "provider": provider,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store.write(payload)
        return state

    def pop(self, state: str) -> Dict[str, str] | None:
        payload = self._store.read({"states": {}})
        states = payload.get("states", {})
        value = states.pop(state, None)
        self._store.write({"states": states})
        return value


OAUTH_STATES = OAuthStateStore()


def authorization_url(provider: IntegrationProvider, *, redirect_uri: str, state: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": provider.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(provider.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return f"{provider.auth_url}?{query}"
