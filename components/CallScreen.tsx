"use client";

import React, { useState, useEffect } from "react";
import AiraLogo from "@/components/AiraLogo";
import { Volume2, VolumeX, Mic, MicOff, PhoneOff } from "lucide-react";

export type CallState = "idle" | "listening" | "speaking" | "ended";

export default function CallScreen() {
  const [callState, setCallState] = useState<CallState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);

  // Handle main circle tap
  const handleOrbClick = () => {
    if (callState === "idle" || callState === "ended") {
      setCallState("listening");
    } else if (callState === "listening") {
      setCallState("speaking");
    } else if (callState === "speaking") {
      setCallState("listening");
    }
  };

  // Handle ending call
  const handleEndCall = () => {
    setCallState("ended");
  };

  // Auto reset ended state back to idle after 1.2 seconds
  useEffect(() => {
    if (callState === "ended") {
      const timer = setTimeout(() => {
        setCallState("idle");
        setIsMuted(false);
        setIsSpeakerOn(true);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [callState]);

  const isActive = callState === "listening" || callState === "speaking";

  return (
    <div className="relative min-h-screen w-full bg-[#000000] text-[#FFFFFF] flex flex-col items-center justify-between py-10 px-6 overflow-hidden select-none font-satoshi">
      {/* Bottom Ambient Glow Bleed (#3954C0 -> #080E29 -> #000000) */}
      <div className="absolute inset-x-0 bottom-0 h-[45%] pointer-events-none ambient-bottom-glow z-0" />

      {/* Top Header Section */}
      <header className="relative z-10 flex flex-col items-center space-y-8 pt-4 w-full max-w-sm">
        {/* Title Logo */}
        <AiraLogo className="h-8 sm:h-9 w-auto" />

        {/* Heading: Satoshi 24px (Regular + Bold) */}
        <div className="text-center">
          <h2 className="text-[24px] tracking-tight text-[#FFFFFF]/90 font-normal leading-tight">
            We Are <span className="font-bold text-[#FFFFFF]">Here to Help</span>
          </h2>
        </div>
      </header>

      {/* Center Interactive Orb Section */}
      <main className="relative z-10 my-auto flex flex-col items-center justify-center">
        {/* Outer Pulsing Ripple Rings */}
        {isActive && (
          <>
            <div className="absolute w-[280px] h-[280px] sm:w-[320px] sm:h-[320px] rounded-full border border-[#3954C0]/30 animate-ripple pointer-events-none" />
            <div className="absolute w-[280px] h-[280px] sm:w-[320px] sm:h-[320px] rounded-full border border-[#080E29]/40 animate-ripple pointer-events-none [animation-delay:1s]" />
          </>
        )}

        {/* Main Orb Button */}
        <button
          onClick={handleOrbClick}
          aria-label={isActive ? "Voice Call Active" : "Tap to Speak"}
          className={`
            relative w-[270px] h-[270px] sm:w-[300px] sm:h-[300px] rounded-full
            aira-orb-gradient cursor-pointer flex items-center justify-center
            transition-all duration-500 ease-out transform outline-none focus:outline-none
            ${
              isActive
                ? "aira-orb-shadow-active animate-orb-pulse scale-[1.02]"
                : "aira-orb-shadow hover:scale-[1.03] active:scale-[0.98]"
            }
          `}
        >
          {/* Subtle Inner Highlight Glass effect */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-transparent via-white/10 to-white/20 pointer-events-none" />

          {/* Button / Label: Satoshi Bold 12px */}
          <span className="relative z-10 text-[#FFFFFF] font-bold text-[12px] tracking-wider uppercase drop-shadow-sm transition-opacity duration-300">
            {callState === "ended"
              ? "Call Ended"
              : callState === "speaking"
              ? "Aira Speaking..."
              : "Tap to Speak"}
          </span>
        </button>
      </main>

      {/* Bottom Controls / Caption Section */}
      <footer className="relative z-10 w-full max-w-sm min-h-[180px] flex flex-col items-center justify-end pb-4">
        {/* Idle State Body Text: Satoshi Regular 14px / Caption */}
        <div
          className={`
            transition-all duration-500 ease-in-out transform
            ${
              callState === "idle"
                ? "opacity-100 translate-y-0 pointer-events-auto"
                : "opacity-0 translate-y-4 pointer-events-none absolute"
            }
          `}
        >
          <p className="text-[11px] sm:text-[12px] text-[#FFFFFF]/70 font-normal tracking-[0.14em] leading-[1.8] text-justify uppercase px-4 max-w-[340px] sm:max-w-[370px]">
            AS YOU SPEAK, AIRA AUTOMATICALLY CAPTURES AND ORGANIZES YOUR SYMPTOMS
            INTO A STRUCTURED MEDICAL SUMMARY. THIS INFORMATION STREAMS DIRECTLY TO
            THE ER TEAM&apos;S DASHBOARD IN REAL TIME, ENABLING DOCTORS TO ASSESS YOUR
            CONDITION AND PREPARE IMMEDIATE CARE WITHOUT LOSING PRECIOUS SECONDS.
          </p>
        </div>

        {/* Active Call Controls Overlay */}
        <div
          className={`
            w-full flex flex-col items-center space-y-6 transition-all duration-500 ease-in-out transform
            ${
              isActive
                ? "opacity-100 translate-y-0 pointer-events-auto"
                : "opacity-0 translate-y-6 pointer-events-none absolute"
            }
          `}
        >
          {/* Top Row: Speaker & Mic Mute Buttons (Gray #575757 background) */}
          <div className="flex items-center justify-center space-x-12">
            {/* Speaker Button */}
            <button
              onClick={() => setIsSpeakerOn(!isSpeakerOn)}
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

            {/* Mic Mute Button */}
            <button
              onClick={() => setIsMuted(!isMuted)}
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

          {/* Bottom Row: Alert Red #FF3714 End Call Button */}
          <div>
            <button
              onClick={handleEndCall}
              aria-label="End Call"
              className="w-16 h-16 rounded-full bg-[#FF3714] hover:bg-[#ff4e2e] text-[#FFFFFF] flex items-center justify-center transition-all duration-200 shadow-xl shadow-[#FF3714]/30 active:scale-95 outline-none"
            >
              <PhoneOff className="w-6 h-6 stroke-[2]" />
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
