from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class VoiceConfig:
    stt_provider: str
    tts_provider: str
    allow_fallback: bool

    whisper_model: str
    whisper_api_key: str | None
    whisper_base_url: str

    deepgram_api_key: str | None
    deepgram_model: str

    google_speech_api_key: str | None
    google_speech_url: str

    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str
    elevenlabs_model: str

    azure_tts_key: str | None
    azure_tts_region: str
    azure_tts_voice: str

    coqui_tts_url: str


    @staticmethod
    def from_env() -> "VoiceConfig":
        return VoiceConfig(
            stt_provider=os.getenv("VOICE_STT_PROVIDER", "whisper").lower(),
            tts_provider=os.getenv("VOICE_TTS_PROVIDER", "elevenlabs").lower(),
            allow_fallback=os.getenv("VOICE_ALLOW_FALLBACK", "true").lower() == "true",
            whisper_model=os.getenv("WHISPER_MODEL", "whisper-1"),
            whisper_api_key=os.getenv("OPENAI_API_KEY"),
            whisper_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            deepgram_api_key=os.getenv("DEEPGRAM_API_KEY"),
            deepgram_model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
            google_speech_api_key=os.getenv("GOOGLE_SPEECH_API_KEY"),
            google_speech_url=os.getenv(
                "GOOGLE_SPEECH_URL",
                "https://speech.googleapis.com/v1/speech:recognize",
            ),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL"),
            elevenlabs_model=os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            azure_tts_key=os.getenv("AZURE_TTS_KEY"),
            azure_tts_region=os.getenv("AZURE_TTS_REGION", "eastus"),
            azure_tts_voice=os.getenv("AZURE_TTS_VOICE", "en-US-JennyNeural"),
            coqui_tts_url=os.getenv("COQUI_TTS_URL", "http://localhost:5002/api/tts"),
        )
