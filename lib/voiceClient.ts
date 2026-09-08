export const ROLE1_BASE = process.env.NEXT_PUBLIC_ARIA_VOICE_URL ?? "/role1";

const WIRE_RATE = 24_000;

const CAPTURE_WORKLET = `
  class CaptureProcessor extends AudioWorkletProcessor {
    constructor() {
      super();
      this._ratio = sampleRate / ${WIRE_RATE};
      this._pos = 0;
      this._prev = 0;
      this._src = null;
      this._out = null;
    }
    _toPcm(samples, len) {
      const pcm = new Int16Array(len);
      for (let i = 0; i < len; i++) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      return pcm;
    }
    process(inputs) {
      const ch = inputs[0]?.[0];
      if (!ch) return true;
      if (this._ratio === 1) {
        const pcm = this._toPcm(ch, ch.length);
        this.port.postMessage(pcm.buffer, [pcm.buffer]);
        return true;
      }
      const n = ch.length;
      if (!this._src || this._src.length < n + 1) {
        this._src = new Float32Array(n + 1);
        this._out = new Float32Array(Math.ceil((n + 1) / this._ratio) + 2);
      }
      const src = this._src;
      const out = this._out;
      src[0] = this._prev;
      src.set(ch, 1);
      let outLen = 0;
      let pos = this._pos;
      while (pos < n) {
        const i = Math.floor(pos);
        const frac = pos - i;
        out[outLen++] = src[i] + (src[i + 1] - src[i]) * frac;
        pos += this._ratio;
      }
      this._pos = pos - n;
      this._prev = ch[n - 1];
      if (outLen) {
        const pcm = this._toPcm(out, outLen);
        this.port.postMessage(pcm.buffer, [pcm.buffer]);
      }
      return true;
    }
  }
  registerProcessor('capture', CaptureProcessor);
`;

const PLAYBACK_WORKLET = `
  class PlaybackProcessor extends AudioWorkletProcessor {
    constructor() {
      super();
      this._ring = new Float32Array(sampleRate * 30);
      this._writePos = 0;
      this._readPos = 0;
      this._available = 0;
      this._step = ${WIRE_RATE} / sampleRate;
      this._rsPos = 0;
      this._rsPrev = 0;
      this._drained = false;
      this.port.onmessage = (e) => {
        if (e.data === 'stop') {
          this._writePos = this._readPos = this._available = 0;
          this._rsPos = this._rsPrev = 0;
          return;
        }
        const int16 = new Int16Array(e.data);
        if (!int16.length) return;
        if (this._drained) {
          this._rsPrev = 0;
          this._rsPos = 0;
          this._drained = false;
        }
        if (this._step === 1) {
          for (let i = 0; i < int16.length; i++) this._push(int16[i] / 32768);
          return;
        }
        const n = int16.length;
        let pos = this._rsPos;
        while (pos < n) {
          const i = Math.floor(pos);
          const frac = pos - i;
          const a = i === 0 ? this._rsPrev : int16[i - 1] / 32768;
          const b = int16[i] / 32768;
          this._push(a + (b - a) * frac);
          pos += this._step;
        }
        this._rsPos = pos - n;
        this._rsPrev = int16[n - 1] / 32768;
      };
    }
    _push(v) {
      if (this._available < this._ring.length) {
        this._ring[this._writePos] = v;
        this._writePos = (this._writePos + 1) % this._ring.length;
        this._available++;
      }
    }
    process(inputs, outputs) {
      const output = outputs[0];
      const out = output[0];
      const cap = this._ring.length;
      for (let i = 0; i < out.length; i++) {
        if (this._available > 0) {
          out[i] = this._ring[this._readPos];
          this._readPos = (this._readPos + 1) % cap;
          this._available--;
        } else {
          out[i] = 0;
          this._drained = true;
        }
      }
      for (let ch = 1; ch < output.length; ch++) output[ch].set(out);
      return true;
    }
  }
  registerProcessor('playback', PlaybackProcessor);
`;

export type VoiceCallState = "idle" | "connecting" | "listening" | "speaking" | "ending" | "ended";

export interface VoiceTurn {
  turnId: string;
  speaker: "patient" | "agent" | "unknown";
  text: string;
  spokenAt: string;
  final: true;
}

export interface VoiceConfig {
  id: string;
  name: string;
  mode: string;
}

export interface HandoffResult {
  caseId: string | null;
  status: number;
}

export interface VoiceSessionHandlers {
  onState: (state: VoiceCallState) => void;
  onCaption?: (speaker: "patient" | "agent", text: string) => void;
  onError?: (message: string) => void;
  onHandoff?: (result: HandoffResult) => void;
}

function blobUrl(code: string): string {
  return URL.createObjectURL(new Blob([code], { type: "application/javascript" }));
}

async function addWorklet(ctx: AudioContext, code: string, name: string): Promise<AudioWorkletNode> {
  const url = blobUrl(code);
  try {
    await ctx.audioWorklet.addModule(url);
  } finally {
    URL.revokeObjectURL(url);
  }
  return new AudioWorkletNode(ctx, name);
}

export async function getVoiceConfig(): Promise<VoiceConfig> {
  const response = await fetch(`${ROLE1_BASE}/config`);
  if (!response.ok) {
    throw new Error("Role 1 voice service is not reachable.");
  }
  return response.json();
}

export async function sendDemoIntake(): Promise<HandoffResult> {
  const response = await fetch(`${ROLE1_BASE}/api/voice/demo-intake`, { method: "POST" });
  const body = await response.json().catch(() => ({}));
  const caseId = body?.intake?.caseId ?? body?.extraction?.payload?.caseId ?? null;
  return { caseId, status: response.status };
}

export class VoiceSession {
  private handlers: VoiceSessionHandlers;
  private ws: WebSocket | null = null;
  private captureCtx: AudioContext | null = null;
  private playbackCtx: AudioContext | null = null;
  private playback: AudioWorkletNode | null = null;
  private playbackGain: GainNode | null = null;
  private mic: MediaStream | null = null;
  private muted = false;
  private speakerOn = true;
  private turns: VoiceTurn[] = [];
  private turnCounter = 0;
  private sessionId: string | null = null;
  private closed = false;
  private autoEndPending = false;

  constructor(handlers: VoiceSessionHandlers) {
    this.handlers = handlers;
  }

  setMuted(value: boolean) {
    this.muted = value;
    this.mic?.getAudioTracks().forEach((track) => {
      track.enabled = !value;
    });
  }

  setSpeakerOn(value: boolean) {
    this.speakerOn = value;
    if (this.playbackGain) this.playbackGain.gain.value = value ? 1 : 0;
  }

  async start(agentId: string) {
    this.closed = false;
    this.autoEndPending = false;
    this.turns = [];
    this.turnCounter = 0;
    this.handlers.onState("connecting");
    const tokenRes = await fetch(`${ROLE1_BASE}/api/voice/token`);
    if (!tokenRes.ok) {
      throw new Error("Could not start a live voice session. Check the AssemblyAI key.");
    }
    const { token } = (await tokenRes.json()) as { token: string };

    this.captureCtx = new AudioContext({ sampleRate: WIRE_RATE });
    this.playbackCtx = new AudioContext({ sampleRate: WIRE_RATE });
    await Promise.all([this.captureCtx.resume(), this.playbackCtx.resume()]);

    this.playback = await addWorklet(this.playbackCtx, PLAYBACK_WORKLET, "playback");
    this.playbackGain = this.playbackCtx.createGain();
    this.playbackGain.gain.value = this.speakerOn ? 1 : 0;
    this.playback.connect(this.playbackGain);
    this.playbackGain.connect(this.playbackCtx.destination);

    this.mic = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: false,
        autoGainControl: false,
      },
    });
    this.mic.getAudioTracks().forEach((track) => {
      track.enabled = !this.muted;
    });
    const capture = await addWorklet(this.captureCtx, CAPTURE_WORKLET, "capture");
    this.captureCtx.createMediaStreamSource(this.mic).connect(capture);

    const url = new URL("wss://agents.assemblyai.com/v1/ws");
    url.searchParams.set("token", token);
    this.ws = new WebSocket(url);
    let ready = false;

    capture.port.onmessage = ({ data }: MessageEvent<ArrayBuffer>) => {
      if (!ready || !this.ws || this.ws.readyState !== 1 || this.muted) return;
      const bytes = new Uint8Array(data);
      let binary = "";
      for (let i = 0; i < bytes.length; i += 0x8000) {
        binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + 0x8000)));
      }
      this.ws.send(JSON.stringify({ type: "input.audio", audio: btoa(binary) }));
    };

    this.ws.onopen = () => {
      this.ws?.send(JSON.stringify({ type: "session.update", session: { agent_id: agentId } }));
    };

    this.ws.onmessage = ({ data }) => {
      const msg = JSON.parse(data as string);
      switch (msg.type) {
        case "session.ready":
          ready = true;
          this.sessionId = msg.session_id ?? this.sessionId;
          this.handlers.onState("listening");
          break;
        case "input.speech.started":
          this.playback?.port.postMessage("stop");
          this.handlers.onState("listening");
          break;
        case "reply.started":
          this.handlers.onState("speaking");
          break;
        case "reply.audio": {
          const raw = atob(msg.data);
          const bytes = new Uint8Array(raw.length);
          for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
          this.playback?.port.postMessage(bytes.buffer, [bytes.buffer]);
          break;
        }
        case "reply.done":
          this.handlers.onState("listening");
          if (msg.status === "interrupted") {
            this.playback?.port.postMessage("stop");
            this.autoEndPending = false;
          } else if (this.autoEndPending) {
            this.autoEndPending = false;
            window.setTimeout(() => {
              if (!this.closed) void this.stop(true);
            }, 1200);
          }
          break;
        case "transcript.user":
          this.pushTurn("patient", msg.text);
          this.handlers.onCaption?.("patient", msg.text);
          break;
        case "transcript.agent":
          this.pushTurn("agent", msg.text);
          this.handlers.onCaption?.("agent", msg.text);
          if (/simulated intake is complete/i.test(msg.text || "")) {
            this.autoEndPending = true;
          }
          break;
        case "session.ended":
          void this.finish();
          break;
        case "session.error":
          this.handlers.onError?.(msg.message || "Voice session error");
          void this.stop(false);
          break;
        default:
          break;
      }
    };

    this.ws.onerror = () => {
      this.handlers.onError?.("Voice connection failed.");
      void this.stop(false);
    };
  }

  async stop(handoff = true) {
    if (this.ws?.readyState === 1) {
      this.handlers.onState("ending");
      this.ws.send(JSON.stringify({ type: "session.end" }));
      const socket = this.ws;
      setTimeout(() => {
        if (socket.readyState === 1) socket.close();
      }, 3000);
      if (handoff) {
        setTimeout(() => {
          void this.finish(true);
        }, 4000);
        return;
      }
    }
    await this.finish(handoff);
  }

  private pushTurn(speaker: "patient" | "agent", text: string) {
    const clean = typeof text === "string" ? text.replace(/\s+/g, " ").trim() : "";
    if (!clean) return;
    this.turns.push({
      turnId: `turn_${++this.turnCounter}`,
      speaker,
      text: clean,
      spokenAt: new Date().toISOString(),
      final: true,
    });
  }

  private async finish(handoff = true) {
    if (this.closed) return;
    this.closed = true;
    this.playback?.port.postMessage("stop");
    this.mic?.getTracks().forEach((track) => track.stop());
    void this.captureCtx?.close();
    void this.playbackCtx?.close();
    this.captureCtx = this.playbackCtx = this.playback = this.playbackGain = this.mic = null;
    if (this.ws && this.ws.readyState < 2) this.ws.close();
    this.ws = null;
    if (handoff && this.turns.some((turn) => turn.speaker === "patient")) {
      try {
        const response = await fetch(`${ROLE1_BASE}/api/voice/handoff`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sessionId: this.sessionId,
            language: "en",
            turns: this.turns,
          }),
        });
        const body = await response.json().catch(() => ({}));
        this.handlers.onHandoff?.({
          caseId: body?.intake?.caseId ?? null,
          status: response.status,
        });
      } catch {
        this.handlers.onError?.("Could not send the transcript to the ER dashboard.");
        this.handlers.onHandoff?.({ caseId: null, status: 0 });
      }
    } else {
      this.handlers.onHandoff?.({ caseId: null, status: 0 });
    }
    this.handlers.onState("ended");
  }
}
