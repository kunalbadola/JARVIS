# JARVIS Voice Pipeline

This repository provides a streaming voice pipeline at `/voice` using WebSocket transport.
The pipeline supports multiple speech-to-text (STT) and text-to-speech (TTS) providers,
streams audio in/out with low-latency chunks, and falls back to text-only mode when the
client does not have microphone access.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## WebSocket protocol

Connect to `/voice` and send control messages as JSON strings:

### Start

```json
{"event": "start", "text_only": false}
```

If `text_only` is `true`, the server will skip STT and only run TTS when you send text.

### Stream audio

Send binary frames containing audio chunks (e.g., 16-bit PCM). When you are done,
send:

```json
{"event": "end"}
```

The server responds with:

```json
{"event": "transcript", "text": "..."}
```

and then streams TTS audio chunks back as binary frames, ending with:

```json
{"event": "tts_end"}
```

### Text-only fallback

If the microphone is unavailable, send text directly:

```json
{"event": "text", "text": "Hello!"}
```

This triggers TTS streaming without requiring audio input.

## Provider configuration

Select providers via environment variables:

```bash
export VOICE_STT_PROVIDER=whisper   # whisper | deepgram | google | mock
export VOICE_TTS_PROVIDER=elevenlabs # elevenlabs | azure | coqui | mock
```

Additional environment variables:

- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `WHISPER_MODEL`
- `DEEPGRAM_API_KEY`, `DEEPGRAM_MODEL`
- `GOOGLE_SPEECH_API_KEY`, `GOOGLE_SPEECH_URL`
- `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL`
- `AZURE_TTS_KEY`, `AZURE_TTS_REGION`, `AZURE_TTS_VOICE`
- `COQUI_TTS_URL`

Set `VOICE_ALLOW_FALLBACK=true` to allow provider fallback to mock providers when
credentials are missing.

## Client app

A minimal Next.js client lives in `client/` with streaming chat, mic capture, and TTS playback.

```bash
cd client
npm install
NEXT_PUBLIC_CHAT_URL=http://localhost:8000/chat \
NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000/voice \
npm run dev
```
