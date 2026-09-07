"use client";

import React from "react";
import { Loader2 } from "lucide-react";

export default function LoadingState() {
  return (
    <div className="flex-1 w-full flex flex-col md:flex-row h-full bg-[#0a0a0f] overflow-hidden">
      {/* Left List Panel Skeleton */}
      <aside className="w-full md:w-[320px] lg:w-[360px] flex-shrink-0 bg-[#0c0c14] border-r border-zinc-800/80 p-4 space-y-4">
        <div className="h-4 bg-zinc-800/70 rounded w-1/2 animate-pulse mb-4" />
        <div className="h-9 bg-zinc-800/50 rounded-lg w-full animate-pulse mb-4" />

        {/* 4 Skeleton Cards */}
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="p-4 rounded-xl border border-zinc-800/60 bg-[#101018] space-y-3 animate-pulse"
          >
            <div className="flex justify-between items-center">
              <div className="h-4 bg-zinc-800 rounded w-1/3" />
              <div className="h-4 bg-zinc-800 rounded w-1/4" />
            </div>
            <div className="h-3 bg-zinc-800/60 rounded w-full" />
            <div className="h-3 bg-zinc-800/40 rounded w-2/3" />
            <div className="flex justify-between pt-2 border-t border-zinc-800/40">
              <div className="h-3 bg-zinc-800/60 rounded w-1/4" />
              <div className="h-3 bg-zinc-800/60 rounded w-1/5" />
            </div>
          </div>
        ))}
      </aside>

      {/* Right Detail Panel Skeleton */}
      <section className="flex-1 p-8 flex flex-col items-center justify-center space-y-4 text-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-2" />
        <div className="h-5 bg-zinc-800/70 rounded w-48 animate-pulse" />
        <div className="h-3 bg-zinc-800/40 rounded w-64 animate-pulse" />
      </section>
    </div>
  );
}
