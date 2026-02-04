from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from ..config import VoiceConfig


class STTError(RuntimeError):
    pass


class STTProvider:
    name = "base"

    async def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError


@dataclass
class WhisperSTT(STTProvider):
    api_key: str
    base_url: str
    model: str
    name: str = "whisper"

    async def transcribe(self, audio_bytes: bytes) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model": self.model}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
        response.raise_for_status()
        payload = response.json()
        return payload.get("text", "")


@dataclass
class DeepgramSTT(STTProvider):
    api_key: str
    model: str
    name: str = "deepgram"

    async def transcribe(self, audio_bytes: bytes) -> str:
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }
        params = {"model": self.model}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers=headers,
                params=params,
                content=audio_bytes,
            )
        response.raise_for_status()
        payload = response.json()
        alternatives = (
            payload.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [])
        )
        if not alternatives:
            return ""
        return alternatives[0].get("transcript", "")


@dataclass
class GoogleSpeechSTT(STTProvider):
    api_key: str
    api_url: str
    name: str = "google"

    async def transcribe(self, audio_bytes: bytes) -> str:
        audio_content = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "config": {"encoding": "LINEAR16", "languageCode": "en-US"},
            "audio": {"content": audio_content},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                params={"key": self.api_key},
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return ""
        return results[0].get("alternatives", [{}])[0].get("transcript", "")


@dataclass
class MockSTT(STTProvider):
    name: str = "mock"

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        return "[mock transcript]"


def build_stt_provider(config: VoiceConfig) -> STTProvider:
    provider = config.stt_provider
    if provider == "whisper":
        if not config.whisper_api_key:
            if config.allow_fallback:
                return MockSTT()
            raise STTError("OPENAI_API_KEY is required for Whisper STT")
        return WhisperSTT(
            api_key=config.whisper_api_key,
            base_url=config.whisper_base_url,
            model=config.whisper_model,
        )
    if provider == "deepgram":
        if not config.deepgram_api_key:
            if config.allow_fallback:
                return MockSTT()
            raise STTError("DEEPGRAM_API_KEY is required for Deepgram STT")
        return DeepgramSTT(api_key=config.deepgram_api_key, model=config.deepgram_model)
    if provider == "google":
        if not config.google_speech_api_key:
            if config.allow_fallback:
                return MockSTT()
            raise STTError("GOOGLE_SPEECH_API_KEY is required for Google STT")
        return GoogleSpeechSTT(
            api_key=config.google_speech_api_key,
            api_url=config.google_speech_url,
        )
    if provider == "mock":
        return MockSTT()
    raise STTError(f"Unknown STT provider: {provider}")
