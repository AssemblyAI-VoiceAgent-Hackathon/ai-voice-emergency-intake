"use client";

import React from "react";
import { ConflictItem } from "@/types/structuredCase";
import { AlertTriangle, CheckCircle2, Circle } from "lucide-react";

interface ConflictCardProps {
  conflict: ConflictItem;
  selectedIndex: number | null;
  onSelectValue: (index: number) => void;
}

export default function ConflictCard({
  conflict,
  selectedIndex,
  onSelectValue,
}: ConflictCardProps) {
  // Convert JSON field path to human readable title
  const formatFieldPath = (path: string) => {
    if (path === "/history/allergies") return "History: Allergies";
    if (path.startsWith("/safetySignals/")) {
      const code = path.replace("/safetySignals/", "").replace(/_/g, " ");
      return `Safety Signal: ${code}`;
    }
    return path
      .replace(/^\//, "")
      .replace(/\//g, " › ")
      .replace(/_/g, " ");
  };

  const isResolved = selectedIndex !== null;
  const statusLabel = isResolved ? "resolved_by_staff" : conflict.status;

  return (
    <div className="bg-[#14161d] border-l-[3px] border-l-amber-500 border border-white/10 rounded-xl p-4 shadow-md space-y-3">
      {/* Top Header: Level 1 Header (11px uppercase muted #8b8d98) + Status badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <h4 className="text-[11px] font-bold uppercase tracking-wider text-[#8b8d98]">
            {formatFieldPath(conflict.fieldPath)}
          </h4>
        </div>

        <span
          className={`text-[11px] font-bold px-2.5 py-0.5 rounded border uppercase tracking-wider flex items-center space-x-1 ${
            isResolved
              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
              : "bg-amber-500/20 text-amber-300 border-amber-500/40"
          }`}
        >
          {isResolved && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
          <span>{statusLabel.replace(/_/g, " ")}</span>
        </span>
      </div>

      <p className="text-[13px] text-[#a1a1aa] font-normal">
        Conflicting statements recorded. Select the verified value below:
      </p>

      {/* Selectable Value Options in #1a1d26 sub-boxes */}
      <div className="space-y-2 pt-1">
        {conflict.values.map((v, idx) => {
          const isSelected = selectedIndex === idx;
          return (
            <button
              type="button"
              key={idx}
              onClick={() => onSelectValue(idx)}
              aria-pressed={isSelected}
              className={`
                w-full text-left p-3.5 rounded-lg border cursor-pointer transition-all duration-200 flex items-start justify-between select-none
                ${
                  isSelected
                    ? "bg-[#3954C0]/25 border-[#3954C0] ring-1 ring-[#3954C0]/60 text-white shadow-md"
                    : "bg-[#1a1d26] hover:bg-[#202430] border-white/10 text-[#a1a1aa] hover:border-white/20"
                }
              `}
            >
              <div className="flex items-start space-x-3">
                <div className="pt-0.5">
                  {isSelected ? (
                    <CheckCircle2 className="w-4.5 h-4.5 text-blue-400" />
                  ) : (
                    <Circle className="w-4.5 h-4.5 text-zinc-500" />
                  )}
                </div>
                <div>
                  {/* Level 2 Primary Content (15-16px, semibold white) */}
                  <div className="text-[15px] sm:text-[16px] font-semibold text-white leading-snug">
                    &quot;{v.value}&quot;
                  </div>
                </div>
              </div>

              {/* Source References */}
              <div className="flex items-center space-x-1 flex-shrink-0 ml-3">
                {v.sourceRefs.map((sr, sIdx) => (
                  <span
                    key={sIdx}
                    className="text-[11px] font-mono text-zinc-300 bg-[#0a0a0f] px-2 py-0.5 rounded border border-white/10"
                  >
                    {sr}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
