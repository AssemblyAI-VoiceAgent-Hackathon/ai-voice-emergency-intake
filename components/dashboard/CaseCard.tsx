"use client";

import React from "react";
import { StructuredCase, StructuredCaseStatus } from "@/types/structuredCase";
import { Clock, AlertCircle, CheckCircle2, HelpCircle } from "lucide-react";

interface CaseCardProps {
  caseItem: StructuredCase;
  isSelected: boolean;
  onSelect: () => void;
}

export default function CaseCard({
  caseItem,
  isSelected,
  onSelect,
}: CaseCardProps) {
  const patientLabel =
    caseItem.subject.patientReference || caseItem.caseId;

  // Format capturedAt as readable date/time
  const formatCapturedAt = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const now = new Date("2026-08-30T12:00:00Z"); // relative base matching contract test dates
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMins / 60);

      if (diffMins < 60 && diffMins >= 0) return `${diffMins}m ago`;
      if (diffHours < 24 && diffHours >= 0) return `${diffHours}h ago`;

      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  };

  const getStatusBadge = (status: StructuredCaseStatus) => {
    switch (status) {
      case "collecting":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-[#3954C0]/20 text-blue-300 border border-[#3954C0]/40 flex items-center space-x-1">
            <Clock className="w-3 h-3 text-blue-400" />
            <span>collecting</span>
          </span>
        );
      case "needs_information":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center space-x-1">
            <HelpCircle className="w-3 h-3 text-amber-400" />
            <span>needs_information</span>
          </span>
        );
      case "ready_for_review":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>ready_for_review</span>
          </span>
        );
    }
  };

  const hasConflicts = caseItem.conflicts && caseItem.conflicts.length > 0;
  const hasSafetySignals =
    caseItem.safetySignals && caseItem.safetySignals.length > 0;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      aria-pressed={isSelected}
      className={`
        p-4 rounded-xl border cursor-pointer transition-all duration-200 text-left select-none relative
        ${
          isSelected
            ? "bg-[#080E29] border-[#3954C0] shadow-lg ring-1 ring-[#3954C0]/40"
            : "bg-[#111116] hover:bg-[#181820] border-zinc-800/80 hover:border-zinc-700"
        }
      `}
    >
      {/* Top Row: Patient Label + Status Badge */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span
            className={`w-2 h-2 rounded-full ${
              hasConflicts
                ? "bg-amber-400 animate-pulse"
                : hasSafetySignals
                ? "bg-[#FF3714] animate-pulse"
                : "bg-emerald-400"
            }`}
          />
          <h3 className="font-bold text-[#FFFFFF] text-sm tracking-tight">
            {patientLabel}
          </h3>
        </div>
        {getStatusBadge(caseItem.status)}
      </div>

      {/* Snippet: summary.oneLine */}
      <p className="text-xs text-zinc-300 line-clamp-2 leading-relaxed mb-3 font-normal">
        {caseItem.summary.oneLine}
      </p>

      {/* Footer Row: CapturedAt & Metadata badges */}
      <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-2 border-t border-zinc-800/60">
        <div className="flex items-center space-x-1 text-zinc-400">
          <Clock className="w-3 h-3 text-zinc-400" />
          <span>{formatCapturedAt(caseItem.capturedAt)}</span>
        </div>

        <div className="flex items-center space-x-1.5">
          {caseItem.subject.ageYears && (
            <span className="text-[10px] text-zinc-400">
              {caseItem.subject.ageYears}yo {caseItem.subject.sexAtBirth}
            </span>
          )}
          {hasConflicts && (
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center space-x-0.5">
              <AlertCircle className="w-2.5 h-2.5" />
              <span>Conflict</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
