from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncGenerator

import httpx

from ..config import VoiceConfig


class TTSError(RuntimeError):
    pass


class TTSProvider:
    name = "base"

    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError

    async def stream(self, text: str, chunk_size: int = 2048) -> AsyncGenerator[bytes, None]:
        audio = await self.synthesize(text)
        for index in range(0, len(audio), chunk_size):
            yield audio[index : index + chunk_size]


@dataclass
class ElevenLabsTTS(TTSProvider):
    api_key: str
    voice_id: str
    model: str
    name: str = "elevenlabs"

    async def synthesize(self, text: str) -> bytes:
        headers = {
            "xi-api-key": self.api_key,
            "Accept": "audio/mpeg",
        }
        payload = {"text": text, "model_id": self.model}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        return response.content


@dataclass
class AzureTTS(TTSProvider):
    api_key: str
    region: str
    voice: str
    name: str = "azure"

    async def synthesize(self, text: str) -> bytes:
        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
        }
        ssml = (
            f"<speak version='1.0' xml:lang='en-US'>"
            f"<voice xml:lang='en-US' name='{self.voice}'>{text}</voice>"
            "</speak>"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=ssml)
        response.raise_for_status()
        return response.content


@dataclass
class CoquiTTS(TTSProvider):
    api_url: str
    name: str = "coqui"

    async def synthesize(self, text: str) -> bytes:
        payload = {"text": text}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.api_url, json=payload)
        response.raise_for_status()
        return response.content


@dataclass
class MockTTS(TTSProvider):
    name: str = "mock"

    async def synthesize(self, text: str) -> bytes:
        return f"[mock audio for {text}]".encode("utf-8")


def build_tts_provider(config: VoiceConfig) -> TTSProvider:
    provider = config.tts_provider
    if provider == "elevenlabs":
        if not config.elevenlabs_api_key:
            if config.allow_fallback:
                return MockTTS()
            raise TTSError("ELEVENLABS_API_KEY is required for ElevenLabs TTS")
        return ElevenLabsTTS(
            api_key=config.elevenlabs_api_key,
            voice_id=config.elevenlabs_voice_id,
            model=config.elevenlabs_model,
        )
    if provider == "azure":
        if not config.azure_tts_key:
            if config.allow_fallback:
                return MockTTS()
            raise TTSError("AZURE_TTS_KEY is required for Azure TTS")
        return AzureTTS(
            api_key=config.azure_tts_key,
            region=config.azure_tts_region,
            voice=config.azure_tts_voice,
        )
    if provider == "coqui":
        return CoquiTTS(api_url=config.coqui_tts_url)
    if provider == "mock":
        return MockTTS()
    raise TTSError(f"Unknown TTS provider: {provider}")
