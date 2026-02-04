from __future__ import annotations

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .voice.pipeline import VoicePipeline, parse_control_message

logging.basicConfig(level=logging.INFO)

app = FastAPI()


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
