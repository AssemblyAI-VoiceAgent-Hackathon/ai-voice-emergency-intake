"use client";

import React from "react";
import Link from "next/link";
import { Activity } from "lucide-react";

export default function EmptyState() {
  return (
    <div
      role="status"
      aria-label="No active cases"
      className="flex-1 w-full bg-[#0a0a0f] text-white flex flex-col items-center justify-center p-6 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-blue-600/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-6">
        <Activity className="w-8 h-8" />
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-white mb-2">
        No active cases
      </h2>

      <p className="text-zinc-400 max-w-sm text-sm leading-relaxed">
        New cases appear here when a patient finishes a call on the Aira intake screen.
      </p>

      <Link
        href="/call"
        className="mt-6 text-sm font-semibold px-4 py-2 rounded-lg bg-[#3954C0] hover:bg-[#4a65d0] text-white"
      >
        Open patient call screen
      </Link>
    </div>
  );
}
