"use client";

import React from "react";
import { DashboardState } from "@/types/dashboard";
import { SlidersHorizontal } from "lucide-react";

interface StateSwitcherProps {
  currentState: DashboardState;
  onStateChange: (newState: DashboardState) => void;
}

export default function StateSwitcher({
  currentState,
  onStateChange,
}: StateSwitcherProps) {
  const states: { key: DashboardState; label: string }[] = [
    { key: "ready", label: "Ready (Cases)" },
    { key: "loading", label: "Loading State" },
    { key: "empty", label: "Empty State" },
    { key: "error", label: "Error State" },
    { key: "unauthorized", label: "Unauthorized" },
  ];

  return (
    <div className="flex items-center space-x-2 bg-zinc-900/90 border border-zinc-800 rounded-lg px-2.5 py-1 text-xs">
      <div className="flex items-center text-zinc-400 font-medium space-x-1.5 pr-1 border-r border-zinc-800">
        <SlidersHorizontal className="w-3.5 h-3.5 text-blue-400" />
        <span className="hidden sm:inline text-[11px] uppercase tracking-wider text-zinc-400">Dev View</span>
      </div>
      <select
        aria-label="Dashboard preview state"
        value={currentState}
        onChange={(e) => onStateChange(e.target.value as DashboardState)}
        className="bg-transparent text-white font-medium focus:outline-none cursor-pointer text-xs py-0.5"
      >
        {states.map((st) => (
          <option key={st.key} value={st.key} className="bg-zinc-900 text-white">
            {st.label}
          </option>
        ))}
      </select>
    </div>
  );
}
