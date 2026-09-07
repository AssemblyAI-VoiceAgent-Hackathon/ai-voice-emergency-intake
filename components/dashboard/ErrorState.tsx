"use client";

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  onRetry: () => void;
  message?: string;
}

export default function ErrorState({ onRetry, message }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex-1 w-full bg-[#0a0a0f] text-white flex flex-col items-center justify-center p-6 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mb-6">
        <AlertTriangle className="w-8 h-8" />
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-white mb-2">
        Couldn&apos;t load cases
      </h2>

      <p className="text-zinc-400 max-w-sm text-sm leading-relaxed mb-6">
        {message ||
          "Unable to reach Role 3. Start python -m src.backend or continue with synthetic contract examples."}
      </p>

      <button
        onClick={onRetry}
        className="px-4 py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-white text-xs font-semibold flex items-center space-x-2 transition-all active:scale-95 shadow-md"
      >
        <RefreshCw className="w-4 h-4 text-blue-400" />
        <span>Retry Connection</span>
      </button>
    </div>
  );
}
