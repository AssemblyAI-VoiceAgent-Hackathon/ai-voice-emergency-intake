"use client";

import React from "react";
import { Lock, LogIn } from "lucide-react";

export default function UnauthorizedState() {
  const handleSignIn = () => {
    console.log("[Aira Dashboard] Staff sign in clicked.");
  };

  return (
    <div className="flex-1 w-full bg-[#0a0a0f] text-white flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center mb-6">
        <Lock className="w-8 h-8 text-blue-400" />
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-white mb-2">
        Staff sign-in required
      </h2>

      <p className="text-zinc-400 max-w-sm text-sm leading-relaxed mb-6">
        This dashboard is restricted to authorized ER staff.
      </p>

      <button
        onClick={handleSignIn}
        className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center space-x-2 transition-all active:scale-95 shadow-lg shadow-blue-600/20"
      >
        <LogIn className="w-4 h-4" />
        <span>Sign in as Staff</span>
      </button>
    </div>
  );
}
