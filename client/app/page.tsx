'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

type Status = 'idle' | 'listening' | 'processing' | 'playing';

const CHAT_ENDPOINT =
  process.env.NEXT_PUBLIC_CHAT_URL ?? 'http://localhost:8000/chat';
const VOICE_WS_ENDPOINT =
  process.env.NEXT_PUBLIC_VOICE_WS_URL ?? 'ws://localhost:8000/voice';
const PCM_SAMPLE_RATE = 16000;

const statusCopy: Record<Status, string> = {
  idle: 'Idle',
  listening: 'Listening',
  processing: 'Processing response',
  playing: 'Playing TTS'
};

const statusClass: Record<Status, string> = {
  idle: '',
  listening: 'listening',
  processing: 'processing',
  playing: 'playing'
};

const toPcm16 = (input: Float32Array) => {
  const buffer = new ArrayBuffer(input.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < input.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return buffer;
};

const pcm16ToFloat32 = (buffer: ArrayBuffer) => {
  const view = new DataView(buffer);
  const float32 = new Float32Array(view.byteLength / 2);
  for (let i = 0; i < float32.length; i += 1) {
    float32[i] = view.getInt16(i * 2, true) / 0x8000;
  }
  return float32;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<Status>('idle');
  const [input, setInput] = useState('');
  const [micActive, setMicActive] = useState(false);

  const streamingAbortRef = useRef<AbortController | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const playbackCursorRef = useRef<number>(0);

  const transcript = useMemo(() => messages, [messages]);

  const appendMessage = useCallback((role: Message['role'], content: string) => {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role, content }]);
  }, []);

  const updateLastAssistant = useCallback((delta: string) => {
    setMessages((prev) => {
      const next = [...prev];
      const lastIndex = next
        .map((message) => message.role)
        .lastIndexOf('assistant');
      if (lastIndex === -1) {
        return prev;
      }
      next[lastIndex] = {
        ...next[lastIndex],
        content: next[lastIndex].content + delta
      };
      return next;
    });
  }, []);

  const ensurePlaybackContext = useCallback(() => {
    if (!playbackContextRef.current) {
      playbackContextRef.current = new AudioContext({ sampleRate: PCM_SAMPLE_RATE });
      playbackCursorRef.current = playbackContextRef.current.currentTime;
    }
    return playbackContextRef.current;
  }, []);

  const playPcmChunk = useCallback(
    (chunk: ArrayBuffer) => {
      const context = ensurePlaybackContext();
      const float32 = pcm16ToFloat32(chunk);
      const buffer = context.createBuffer(1, float32.length, PCM_SAMPLE_RATE);
      buffer.copyToChannel(float32, 0);
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      const startAt = Math.max(context.currentTime, playbackCursorRef.current);
      source.start(startAt);
      playbackCursorRef.current = startAt + buffer.duration;
    },
    [ensurePlaybackContext]
  );

  const playTts = useCallback(
    async (text: string) => {
      if (!text.trim()) return;
      setStatus('playing');
      const socket = new WebSocket(VOICE_WS_ENDPOINT);
      socket.binaryType = 'arraybuffer';
      socket.onopen = () => {
        socket.send(JSON.stringify({ event: 'start', text_only: true }));
        socket.send(JSON.stringify({ event: 'text', text }));
      };
      socket.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const payload = JSON.parse(event.data);
            if (payload.event === 'tts_end') {
              socket.close();
              setStatus('idle');
            }
          } catch (error) {
            console.error('Failed to parse TTS payload', error);
          }
          return;
        }
        playPcmChunk(event.data as ArrayBuffer);
      };
      socket.onerror = (error) => {
        console.error('TTS socket error', error);
        setStatus('idle');
      };
    },
    [playPcmChunk]
  );

  const streamChat = useCallback(
    async (text: string) => {
      streamingAbortRef.current?.abort();
      const abortController = new AbortController();
      streamingAbortRef.current = abortController;
      setStatus('processing');
      appendMessage('assistant', '');

      const response = await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
        signal: abortController.signal
      });

      if (!response.body) {
        throw new Error('Missing stream body from /chat');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;
        updateLastAssistant(chunk);
      }
      setStatus('idle');
      await playTts(fullText);
    },
    [appendMessage, playTts, updateLastAssistant]
  );

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;
    const text = input.trim();
    setInput('');
    appendMessage('user', text);
    try {
      await streamChat(text);
    } catch (error) {
      console.error(error);
      setStatus('idle');
    }
  }, [appendMessage, input, streamChat]);

  const stopMic = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    micStreamRef.current?.getTracks().forEach((track) => track.stop());
    micStreamRef.current = null;
    voiceSocketRef.current?.send(JSON.stringify({ event: 'end' }));
    voiceSocketRef.current?.close();
    voiceSocketRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
    setMicActive(false);
    setStatus('idle');
  }, []);

  const startMic = useCallback(async () => {
    try {
      const socket = new WebSocket(VOICE_WS_ENDPOINT);
      socket.binaryType = 'arraybuffer';
      voiceSocketRef.current = socket;
      socket.onopen = async () => {
        socket.send(JSON.stringify({ event: 'start', text_only: false }));
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStreamRef.current = stream;
        const audioContext = new AudioContext({ sampleRate: PCM_SAMPLE_RATE });
        audioContextRef.current = audioContext;
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;
        source.connect(processor);
        processor.connect(audioContext.destination);
        processor.onaudioprocess = (event) => {
          if (socket.readyState !== WebSocket.OPEN) return;
          const inputBuffer = event.inputBuffer.getChannelData(0);
          socket.send(toPcm16(inputBuffer));
        };
        setStatus('listening');
        setMicActive(true);
      };
      socket.onmessage = (event) => {
        if (typeof event.data === 'string') {
          try {
            const payload = JSON.parse(event.data);
            if (payload.event === 'transcript') {
              appendMessage('user', payload.text);
              appendMessage('assistant', '');
              setStatus('processing');
              streamChat(payload.text).catch((error) => {
                console.error(error);
                setStatus('idle');
              });
            }
            if (payload.event === 'tts_end') {
              setStatus('idle');
            }
          } catch (error) {
            console.error('Failed to parse voice payload', error);
          }
          return;
        }
        playPcmChunk(event.data as ArrayBuffer);
      };
      socket.onclose = () => {
        setMicActive(false);
      };
      socket.onerror = (error) => {
        console.error('Voice socket error', error);
        stopMic();
      };
    } catch (error) {
      console.error('Failed to start microphone', error);
      stopMic();
    }
  }, [appendMessage, playPcmChunk, stopMic, streamChat]);

  useEffect(() => {
    return () => {
      streamingAbortRef.current?.abort();
      stopMic();
    };
  }, [stopMic]);

  return (
    <main>
      <header>
        <h1>JARVIS Client</h1>
        <p>Stream chat responses from /chat and capture audio for live transcripts.</p>
        <div className="status">
          <span className={`status-dot ${statusClass[status]}`} />
          <span>{statusCopy[status]}</span>
        </div>
      </header>

      <section className="card">
        <div className="transcript">
          {transcript.length === 0 ? (
            <p className="footer-note">No messages yet. Start typing or use the mic.</p>
          ) : (
            transcript.map((message) => (
              <div key={message.id} className={`message ${message.role}`}>
                {message.content || '...'}
              </div>
            ))
          )}
        </div>

        <div className="controls">
          <input
            type="text"
            placeholder="Type a message"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                handleSend();
              }
            }}
          />
          <button type="button" onClick={handleSend} disabled={status !== 'idle'}>
            Send
          </button>
        </div>

        <div className="controls" style={{ gridTemplateColumns: 'auto 1fr' }}>
          <button
            type="button"
            className="mic"
            onClick={() => (micActive ? stopMic() : startMic())}
          >
            <span className="mic-indicator" />
            {micActive ? 'Stop Mic' : 'Start Mic'}
          </button>
          <p className="footer-note">
            Uses WebSocket audio streaming to /voice and plays TTS responses.
          </p>
        </div>
      </section>
    </main>
  );
}
