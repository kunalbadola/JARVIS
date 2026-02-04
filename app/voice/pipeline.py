from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .config import VoiceConfig
from .providers.stt import STTProvider, build_stt_provider
from .providers.tts import TTSProvider, build_tts_provider

logger = logging.getLogger(__name__)


@dataclass
class VoiceSession:
    stt_provider: STTProvider
    tts_provider: TTSProvider
    audio_buffer: bytearray = field(default_factory=bytearray)
    text_only: bool = False

    async def add_audio_chunk(self, chunk: bytes) -> None:
        if self.text_only:
            return
        self.audio_buffer.extend(chunk)

    async def flush_audio(self) -> str:
        if not self.audio_buffer:
            return ""
        audio_bytes = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        return await self.stt_provider.transcribe(audio_bytes)

    async def stream_tts(self, text: str, websocket) -> None:
        if not text:
            return
        async for chunk in self.tts_provider.stream(text):
            await websocket.send_bytes(chunk)
        await websocket.send_text(json.dumps({"event": "tts_end"}))


@dataclass
class VoicePipeline:
    stt_provider: STTProvider
    tts_provider: TTSProvider

    @classmethod
    def from_env(cls) -> "VoicePipeline":
        config = VoiceConfig.from_env()
        stt_provider = build_stt_provider(config)
        tts_provider = build_tts_provider(config)
        logger.info(
            "Voice pipeline configured with STT=%s TTS=%s",
            stt_provider.name,
            tts_provider.name,
        )
        return cls(stt_provider=stt_provider, tts_provider=tts_provider)

    def new_session(self, text_only: bool) -> VoiceSession:
        return VoiceSession(
            stt_provider=self.stt_provider,
            tts_provider=self.tts_provider,
            text_only=text_only,
        )


def parse_control_message(message: str) -> dict[str, Any]:
    try:
        return json.loads(message)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid control message JSON") from exc
