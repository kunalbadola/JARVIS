from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.agent.router import run_agent
from app.integrations.oauth import OAUTH_STATES, PROVIDERS, authorization_url
from app.privacy import PRIVACY_POLICY
from app.storage.audit_log import AUDIT_LOGGER
from app.storage.consent_store import CONSENT_STORE
from app.storage.privacy_store import PRIVACY_STORE, PrivacySettings
from app.storage.secrets_store import SECRETS_MANAGER
from .voice.pipeline import VoicePipeline, parse_control_message

logging.basicConfig(level=logging.INFO)

app = FastAPI()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    provider: str = "stub"


class ConsentResolution(BaseModel):
    approved: bool


class OAuthStartRequest(BaseModel):
    provider: str
    redirect_uri: str


class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str
    state: str


class PrivacySettingsRequest(BaseModel):
    retention_days: int = Field(..., ge=1, le=3650)
    data_export_enabled: bool
    delete_on_request: bool


@app.post("/chat")
async def chat_endpoint(payload: ChatRequest) -> PlainTextResponse:
    response = run_agent(payload.message, payload.provider)
    AUDIT_LOGGER.append(
        "chat_received",
        actor="user",
        details={
            "intent": response.intent,
            "provider": response.provider,
            "tool_calls": [tool_call.name for tool_call in response.tool_calls],
        },
    )
    return PlainTextResponse(response.completion.get("completion", ""))


@app.get("/integrations/providers")
async def list_integration_providers() -> List[Dict[str, Any]]:
    secrets = {record.key for record in SECRETS_MANAGER.list_secrets()}
    return [
        {
            "name": provider.name,
            "label": provider.label,
            "scopes": provider.scopes,
            "connected": f"oauth:{provider.name}" in secrets,
        }
        for provider in PROVIDERS.values()
    ]


@app.post("/integrations/oauth/start")
async def start_oauth(request: OAuthStartRequest) -> Dict[str, str]:
    provider = PROVIDERS.get(request.provider)
    if not provider:
        raise HTTPException(status_code=404, detail="Unknown provider")
    state = OAUTH_STATES.create(request.provider, request.redirect_uri)
    auth_url = authorization_url(provider, redirect_uri=request.redirect_uri, state=state)
    AUDIT_LOGGER.append(
        "oauth_started",
        actor="user",
        details={"provider": request.provider, "redirect_uri": request.redirect_uri},
    )
    return {"auth_url": auth_url, "state": state}


@app.post("/integrations/oauth/callback")
async def oauth_callback(request: OAuthCallbackRequest) -> Dict[str, Any]:
    provider = PROVIDERS.get(request.provider)
    if not provider:
        raise HTTPException(status_code=404, detail="Unknown provider")
    state = OAUTH_STATES.pop(request.state)
    if not state or state.get("provider") != request.provider:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    token_payload = {
        "provider": request.provider,
        "code": request.code,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    record = SECRETS_MANAGER.set_secret(
        f"oauth:{request.provider}",
        json.dumps(token_payload),
        metadata={"provider": request.provider, "scopes": provider.scopes},
    )
    AUDIT_LOGGER.append(
        "oauth_completed",
        actor="user",
        details={"provider": request.provider, "secret_key": record.key},
    )
    return {"status": "connected", "provider": request.provider}


@app.delete("/integrations/{provider}")
async def disconnect_integration(provider: str) -> Dict[str, Any]:
    deleted = SECRETS_MANAGER.delete_secret(f"oauth:{provider}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not connected")
    AUDIT_LOGGER.append(
        "oauth_disconnected",
        actor="user",
        details={"provider": provider},
    )
    return {"status": "disconnected", "provider": provider}


@app.get("/consent/requests")
async def list_consent_requests(status: Optional[str] = None) -> List[Dict[str, Any]]:
    requests = CONSENT_STORE.list(status=status)
    return [request.__dict__ for request in requests]


@app.post("/consent/requests/{request_id}/resolve")
async def resolve_consent(request_id: str, payload: ConsentResolution) -> Dict[str, Any]:
    updated = CONSENT_STORE.resolve(request_id, approved=payload.approved)
    if not updated:
        raise HTTPException(status_code=404, detail="Consent request not found")
    AUDIT_LOGGER.append(
        "consent_resolved",
        actor="user",
        details={"request_id": request_id, "approved": payload.approved},
    )
    return updated.__dict__


@app.get("/audit/logs")
async def list_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    entries = AUDIT_LOGGER.list_entries(limit=limit)
    return [entry.__dict__ for entry in entries]


@app.get("/privacy/policy")
async def get_privacy_policy() -> Dict[str, str]:
    return {"policy": PRIVACY_POLICY}


@app.get("/privacy/settings")
async def get_privacy_settings() -> PrivacySettings:
    return PRIVACY_STORE.load()


@app.put("/privacy/settings")
async def update_privacy_settings(payload: PrivacySettingsRequest) -> PrivacySettings:
    settings = PrivacySettings(
        retention_days=payload.retention_days,
        data_export_enabled=payload.data_export_enabled,
        delete_on_request=payload.delete_on_request,
    )
    saved = PRIVACY_STORE.save(settings)
    AUDIT_LOGGER.append(
        "privacy_settings_updated",
        actor="user",
        details=saved.__dict__,
    )
    return saved


@app.websocket("/voice")
async def voice_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    pipeline = VoicePipeline.from_env()
    session = pipeline.new_session(text_only=False)

    try:
        while True:
            message = await websocket.receive()
            if "text" in message:
                payload = parse_control_message(message["text"])
                event = payload.get("event")

                if event == "start":
                    session.text_only = payload.get("text_only", False)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "ready",
                                "mode": "text" if session.text_only else "audio",
                            }
                        )
                    )
                elif event == "text":
                    text = payload.get("text", "")
                    await websocket.send_text(
                        json.dumps({"event": "transcript", "text": text})
                    )
                    await session.stream_tts(text, websocket)
                elif event == "end":
                    transcript = await session.flush_audio()
                    await websocket.send_text(
                        json.dumps({"event": "transcript", "text": transcript})
                    )
                    await session.stream_tts(transcript, websocket)
                else:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "error",
                                "message": f"Unknown event: {event}",
                            }
                        )
                    )
            elif "bytes" in message:
                await session.add_audio_chunk(message["bytes"])
    except WebSocketDisconnect:
        return
