import Link from "next/link";
import AiraLogo from "@/components/AiraLogo";
import { Phone, LayoutDashboard, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white flex flex-col items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Background ambient lighting */}
      <div className="absolute inset-0 pointer-events-none ambient-bottom-glow" />

      <main className="relative z-10 w-full max-w-md flex flex-col items-center text-center space-y-8">
        {/* Logo */}
        <AiraLogo className="h-10 w-auto mb-2" />

        <p className="text-zinc-400 text-sm max-w-sm leading-relaxed">
          Voice intake for patients. Live review for ER staff.
        </p>

        {/* Portal Cards */}
        <div className="w-full space-y-4 pt-4">
          <Link
            href="/call"
            className="group w-full p-5 rounded-2xl bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border border-blue-500/30 hover:border-blue-500/60 flex items-center justify-between transition-all duration-300 shadow-lg hover:shadow-blue-500/10 active:scale-[0.98]"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center border border-blue-500/30 group-hover:scale-105 transition-transform">
                <Phone className="w-6 h-6" />
              </div>
              <div className="text-left">
                <div className="font-semibold text-white text-base">Patient call</div>
                <div className="text-xs text-zinc-400">Talk with Aira. The summary goes to staff.</div>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-blue-400 group-hover:translate-x-1 transition-transform" />
          </Link>

          <Link
            href="/dashboard"
            className="group w-full p-5 rounded-2xl bg-zinc-900/50 hover:bg-zinc-900/80 border border-zinc-800 hover:border-zinc-700 flex items-center justify-between transition-all duration-300 shadow-md active:scale-[0.98]"
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-xl bg-zinc-800 text-zinc-300 flex items-center justify-center border border-zinc-700 group-hover:scale-105 transition-transform">
                <LayoutDashboard className="w-6 h-6" />
              </div>
              <div className="text-left">
                <div className="font-semibold text-white text-base">Staff dashboard</div>
                <div className="text-xs text-zinc-400">Review live intake, edit, and approve.</div>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </main>
    </div>
  );
}
