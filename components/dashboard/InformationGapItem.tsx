"use client";

import React, { useState } from "react";
import { InformationGap } from "@/types/structuredCase";
import { CheckCircle2, HelpCircle, X } from "lucide-react";

interface InformationGapItemProps {
  gap: InformationGap;
  isResolved: boolean;
  onResolve: (value: string, reason: string) => void;
}

export default function InformationGapItem({
  gap,
  isResolved,
  onResolve,
}: InformationGapItemProps) {
  const [resolveOpen, setResolveOpen] = useState(false);
  const [answerDraft, setAnswerDraft] = useState("");
  const [reasonDraft, setReasonDraft] = useState("Answered during review");
  const [reasonError, setReasonError] = useState(false);

  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "required":
        return "bg-[#FF3714]/20 text-[#FF3714] border-[#FF3714]/40 font-bold";
      case "recommended":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold";
      case "optional":
      default:
        return "bg-zinc-800 text-zinc-300 border-zinc-700 font-semibold";
    }
  };

  const handleMarkResolved = () => {
    if (!reasonDraft.trim()) {
      setReasonError(true);
      return;
    }
    onResolve(answerDraft.trim(), reasonDraft.trim());
    setResolveOpen(false);
  };

  // ── Resolved state ─────────────────────────────────────────────────────────
  if (isResolved) {
    return (
      <div className="bg-[#14161d] border-l-[3px] border-l-emerald-500 border border-white/8 rounded-xl p-4 shadow-md opacity-60">
        <div className="flex items-start justify-between space-x-4">
          <div className="space-y-1">
            <div className="flex items-start space-x-2 text-[14px] font-semibold text-zinc-400 leading-snug line-through">
              <HelpCircle className="w-4 h-4 text-zinc-500 flex-shrink-0 mt-0.5" />
              <span>{gap.question}</span>
            </div>
            <div className="text-[12px] font-mono text-[#6b6d78] pl-6">
              {gap.fieldPath}
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <span className={`text-[11px] px-2.5 py-1 rounded border uppercase tracking-wider ${getPriorityStyle(gap.priority)}`}>
              {gap.priority}
            </span>
            <span className="flex items-center space-x-1 text-[11px] px-2.5 py-1 rounded border bg-emerald-500/15 text-emerald-400 border-emerald-500/40 font-bold uppercase tracking-wider">
              <CheckCircle2 className="w-3 h-3" />
              <span>Resolved</span>
            </span>
          </div>
        </div>
      </div>
    );
  }

  // ── Unresolved state ────────────────────────────────────────────────────────
  return (
    <div className="bg-[#14161d] border-l-[3px] border-l-amber-500 border border-white/10 rounded-xl p-4 shadow-md space-y-3">
      {/* Header row */}
      <div className="flex items-start justify-between space-x-4">
        <div className="space-y-1 flex-1">
          <div className="flex items-start space-x-2 text-[15px] sm:text-[16px] font-semibold text-white leading-snug">
            <HelpCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <span>{gap.question}</span>
          </div>
          <div className="text-[12px] font-mono text-[#a1a1aa] pl-6">
            Target Path: {gap.fieldPath}
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <span
            className={`text-[11px] px-2.5 py-1 rounded border uppercase tracking-wider ${getPriorityStyle(gap.priority)}`}
          >
            {gap.priority}
          </span>
          <button
            onClick={() => setResolveOpen((v) => !v)}
            className="text-[11px] px-2.5 py-1 rounded border uppercase tracking-wider font-bold bg-amber-500/10 text-amber-300 border-amber-500/40 hover:bg-amber-500/20 transition-colors"
          >
            {resolveOpen ? "Cancel" : "Resolve ↓"}
          </button>
        </div>
      </div>

      {/* Inline resolve form */}
      {resolveOpen && (
        <div className="space-y-2.5 pt-1 border-t border-white/8">
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold">
              Answer / Value
            </label>
            <input
              type="text"
              value={answerDraft}
              onChange={(e) => setAnswerDraft(e.target.value)}
              placeholder="Enter answer..."
              className="w-full bg-[#0a0a0f] border border-white/10 rounded-lg px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none focus:border-amber-500/50 transition-colors"
              autoFocus
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold">
              Reason for change <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={reasonDraft}
              onChange={(e) => {
                setReasonDraft(e.target.value);
                setReasonError(false);
              }}
              placeholder="Required — e.g. Answered during review"
              className={`w-full bg-[#0a0a0f] border rounded-lg px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none transition-colors ${
                reasonError
                  ? "border-red-500/60 focus:border-red-500"
                  : "border-white/10 focus:border-amber-500/50"
              }`}
            />
            {reasonError && (
              <p className="text-[11px] text-red-400">Reason is required.</p>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleMarkResolved}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500 text-black text-[12px] font-bold hover:bg-amber-400 transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Mark Resolved</span>
            </button>
            <button
              onClick={() => {
                setResolveOpen(false);
                setReasonError(false);
              }}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#1a1d26] text-[#a1a1aa] text-[12px] font-semibold hover:text-white border border-white/10 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              <span>Cancel</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
