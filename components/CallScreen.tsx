"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import AiraLogo from "@/components/AiraLogo";
import { Volume2, VolumeX, Mic, MicOff, PhoneOff, LayoutDashboard, CheckCircle2 } from "lucide-react";
import {
  VoiceSession,
  VoiceCallState,
  getVoiceConfig,
  sendDemoIntake,
  type VoiceConfig,
} from "@/lib/voiceClient";

type Caption = { speaker: "patient" | "agent"; text: string };

function orbLabel(callState: VoiceCallState, sending: boolean) {
  if (sending) return "Sending to ER...";
  if (callState === "ended") return "Call Ended";
  if (callState === "connecting") return "Connecting...";
  if (callState === "ending") return "Wrapping up...";
  if (callState === "speaking") return "Aira Speaking...";
  if (callState === "listening") return "Listening...";
  return "Tap to Speak";
}

export default function CallScreen() {
  const sessionRef = useRef<VoiceSession | null>(null);
  const [callState, setCallState] = useState<VoiceCallState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<VoiceConfig | null>(null);
  const [sending, setSending] = useState(false);
  const [sentCaseId, setSentCaseId] = useState<string | null>(null);
  const captionsEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    captionsEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [captions]);

  useEffect(() => {
    getVoiceConfig()
      .then(setConfig)
      .catch(() => setError("Voice intake is unavailable. Start Role 1, then try again."));
    return () => {
      void sessionRef.current?.stop(false);
    };
  }, []);

  const resetCall = () => {
    setCallState("idle");
    setCaptions([]);
    setSending(false);
    setSentCaseId(null);
    setError(null);
    sessionRef.current = null;
  };

  const handleOrbClick = async () => {
    if (callState !== "idle" && callState !== "ended") return;
    if (sentCaseId) {
      resetCall();
      return;
    }
    if (!config?.id) {
      setError(
        config?.mode === "demo"
          ? "Live voice is not connected. You can still send a demo case to the ER dashboard."
          : "Voice agent is not ready."
      );
      return;
    }
    setError(null);
    setCaptions([]);
    setSentCaseId(null);
    const session = new VoiceSession({
      onState: setCallState,
      onCaption: (speaker, text) => {
        setCaptions((prev) => [...prev.slice(-4), { speaker, text }]);
      },
      onError: (message) => setError(message),
      onHandoff: (result) => {
        setSending(false);
        if (result.caseId) {
          setSentCaseId(result.caseId);
          setCallState("ended");
        } else {
          setCallState("idle");
        }
      },
    });
    session.setMuted(isMuted);
    session.setSpeakerOn(isSpeakerOn);
    sessionRef.current = session;
    try {
      await session.start(config.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the call.");
      setCallState("idle");
      sessionRef.current = null;
    }
  };

  const handleEndCall = () => {
    setSending(true);
    void sessionRef.current?.stop(true);
  };

  const handleDemoIntake = async () => {
    setSending(true);
    setError(null);
    try {
      const result = await sendDemoIntake();
      if (!result.caseId) {
        throw new Error("The ER dashboard did not receive a case.");
      }
      setSentCaseId(result.caseId);
      setCallState("ended");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send a case to the ER team.");
    } finally {
      setSending(false);
    }
  };

  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    sessionRef.current?.setMuted(next);
  };

  const toggleSpeaker = () => {
    const next = !isSpeakerOn;
    setIsSpeakerOn(next);
    sessionRef.current?.setSpeakerOn(next);
  };

  const isActive = callState === "listening" || callState === "speaking" || callState === "connecting";
  const showControls = isActive || callState === "ending" || sending;
  const liveReady = Boolean(config?.id && config.mode === "live");

  return (
    <div className="relative min-h-screen w-full bg-[#000000] text-[#FFFFFF] flex flex-col items-center justify-between py-8 px-6 overflow-hidden select-none font-satoshi">
      <div className="absolute inset-x-0 bottom-0 h-[45%] pointer-events-none ambient-bottom-glow z-0" />

      <header className="relative z-10 flex flex-col items-center space-y-5 pt-2 w-full max-w-sm">
        <div className="w-full flex items-center justify-between">
          <AiraLogo className="h-7 w-auto" />
          <Link
            href="/dashboard"
            className="flex items-center space-x-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 hover:text-white bg-zinc-900/80 border border-zinc-800 rounded-full px-3 py-1.5"
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Staff</span>
          </Link>
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-[24px] tracking-tight text-[#FFFFFF]/90 font-normal leading-tight">
            We Are <span className="font-bold text-[#FFFFFF]">Here to Help</span>
          </h2>
          <p className="text-[10px] uppercase tracking-[0.18em] text-zinc-500">
            {liveReady ? "Live voice intake" : "Voice intake"}
          </p>
        </div>
      </header>

      <main className="relative z-10 my-auto flex flex-col items-center justify-center w-full max-w-sm">
        {sentCaseId ? (
          <div className="flex flex-col items-center text-center space-y-4 px-4">
            <div className="w-20 h-20 rounded-full bg-emerald-500/15 border border-emerald-400/40 flex items-center justify-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-300" />
            </div>
            <h3 className="text-xl font-semibold">Sent to the ER team</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Aira captured your conversation and opened it on the staff dashboard for review.
            </p>
            <div className="flex flex-col w-full gap-2 pt-2">
              <Link
                href={`/dashboard?caseId=${encodeURIComponent(sentCaseId)}`}
                className="w-full text-center text-[13px] font-semibold px-4 py-3 rounded-xl bg-[#3954C0] hover:bg-[#4a65d0]"
              >
                Open staff dashboard
              </Link>
              <button
                type="button"
                onClick={resetCall}
                className="w-full text-[13px] font-semibold px-4 py-3 rounded-xl bg-zinc-900 border border-zinc-700 hover:bg-zinc-800"
              >
                Start another call
              </button>
            </div>
          </div>
        ) : (
          <>
            {isActive && (
              <>
                <div className="absolute w-[280px] h-[280px] sm:w-[320px] sm:h-[320px] rounded-full border border-[#3954C0]/30 animate-ripple pointer-events-none" />
                <div className="absolute w-[280px] h-[280px] sm:w-[320px] sm:h-[320px] rounded-full border border-[#080E29]/40 animate-ripple pointer-events-none [animation-delay:1s]" />
              </>
            )}

            <button
              onClick={() => void handleOrbClick()}
              aria-label={isActive ? "Voice Call Active" : "Tap to Speak"}
              disabled={showControls}
              className={`
                relative w-[270px] h-[270px] sm:w-[300px] sm:h-[300px] rounded-full
                aira-orb-gradient flex items-center justify-center
                transition-all duration-500 ease-out transform outline-none focus:outline-none
                ${showControls ? "cursor-default" : "cursor-pointer"}
                ${
                  isActive
                    ? "aira-orb-shadow-active animate-orb-pulse scale-[1.02]"
                    : "aira-orb-shadow hover:scale-[1.03] active:scale-[0.98]"
                }
              `}
            >
              <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-transparent via-white/10 to-white/20 pointer-events-none" />
              <span className="relative z-10 text-[#FFFFFF] font-bold text-[12px] tracking-wider uppercase drop-shadow-sm transition-opacity duration-300 px-6 text-center">
                {orbLabel(callState, sending)}
              </span>
            </button>

            {captions.length > 0 && (
              <div className="mt-6 w-full space-y-2 max-h-36 overflow-y-auto custom-scrollbar px-1">
                {captions.map((line, index) => (
                  <p
                    key={`${line.speaker}-${index}`}
                    className={`text-[13px] leading-relaxed px-3 py-2 rounded-2xl ${
                      line.speaker === "agent"
                        ? "bg-[#3954C0]/20 text-blue-100 text-left"
                        : "bg-zinc-900 text-zinc-200 text-right"
                    }`}
                  >
                    <span className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-0.5">
                      {line.speaker === "agent" ? "Aira" : "You"}
                    </span>
                    {line.text}
                  </p>
                ))}
                <div ref={captionsEndRef} />
              </div>
            )}
          </>
        )}
      </main>

      <footer className="relative z-10 w-full max-w-sm min-h-[160px] flex flex-col items-center justify-end pb-2">
        {!sentCaseId && (
          <>
            <div
              className={`
                transition-all duration-500 ease-in-out transform
                ${
                  callState === "idle" || callState === "ended"
                    ? "opacity-100 translate-y-0 pointer-events-auto"
                    : "opacity-0 translate-y-4 pointer-events-none absolute"
                }
              `}
            >
              <p className="text-[11px] sm:text-[12px] text-[#FFFFFF]/70 font-normal tracking-[0.14em] leading-[1.8] text-justify uppercase px-4 max-w-[340px] sm:max-w-[370px]">
                As you speak, Aira captures your symptoms into a structured summary
                for the ER team. A clinician reviews everything before any triage
                decision is made.
              </p>
              {error && (
                <p className="mt-4 px-4 text-center text-[12px] text-[#FF3714] leading-relaxed">{error}</p>
              )}
              <button
                type="button"
                onClick={() => void handleDemoIntake()}
                disabled={sending}
                className="mt-5 mx-auto block text-[11px] font-semibold tracking-wide uppercase px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              >
                Send a demo case to staff
              </button>
            </div>

            <div
              className={`
                w-full flex flex-col items-center space-y-6 transition-all duration-500 ease-in-out transform
                ${
                  showControls
                    ? "opacity-100 translate-y-0 pointer-events-auto"
                    : "opacity-0 translate-y-6 pointer-events-none absolute"
                }
              `}
            >
              <div className="flex items-center justify-center space-x-12">
                <button
                  onClick={toggleSpeaker}
                  aria-label={isSpeakerOn ? "Mute Speaker" : "Unmute Speaker"}
                  className={`
                    w-16 h-16 rounded-full flex items-center justify-center
                    transition-all duration-200 outline-none shadow-lg active:scale-95
                    ${
                      isSpeakerOn
                        ? "bg-[#575757] hover:bg-[#686868] text-[#FFFFFF]"
                        : "bg-[#3954C0] hover:bg-[#4865d5] text-[#FFFFFF]"
                    }
                  `}
                >
                  {isSpeakerOn ? (
                    <Volume2 className="w-6 h-6 stroke-[1.75]" />
                  ) : (
                    <VolumeX className="w-6 h-6 stroke-[1.75]" />
                  )}
                </button>

                <button
                  onClick={toggleMute}
                  aria-label={isMuted ? "Unmute Microphone" : "Mute Microphone"}
                  className={`
                    w-16 h-16 rounded-full flex items-center justify-center
                    transition-all duration-200 outline-none shadow-lg active:scale-95
                    ${
                      !isMuted
                        ? "bg-[#575757] hover:bg-[#686868] text-[#FFFFFF]"
                        : "bg-[#FF3714]/20 border border-[#FF3714] text-[#FF3714]"
                    }
                  `}
                >
                  {isMuted ? (
                    <MicOff className="w-6 h-6 stroke-[1.75]" />
                  ) : (
                    <Mic className="w-6 h-6 stroke-[1.75]" />
                  )}
                </button>
              </div>

              <button
                onClick={handleEndCall}
                aria-label="End Call"
                className="w-16 h-16 rounded-full bg-[#FF3714] hover:bg-[#ff4e2e] text-[#FFFFFF] flex items-center justify-center transition-all duration-200 shadow-xl shadow-[#FF3714]/30 active:scale-95 outline-none"
              >
                <PhoneOff className="w-6 h-6 stroke-[2]" />
              </button>
            </div>
          </>
        )}
      </footer>
    </div>
  );
}
