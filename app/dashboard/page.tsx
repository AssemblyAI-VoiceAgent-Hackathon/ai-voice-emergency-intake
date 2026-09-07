"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DashboardState } from "@/types/dashboard";
import { StructuredCase } from "@/types/structuredCase";
import contractCasesData from "@/contracts/examples/structured-case.example.json";
import StateSwitcher from "@/components/dashboard/StateSwitcher";
import CaseList from "@/components/dashboard/CaseList";
import CaseDetail from "@/components/dashboard/CaseDetail";
import LoadingState from "@/components/dashboard/LoadingState";
import EmptyState from "@/components/dashboard/EmptyState";
import ErrorState from "@/components/dashboard/ErrorState";
import UnauthorizedState from "@/components/dashboard/UnauthorizedState";
import AiraLogo from "@/components/AiraLogo";
import { ArrowLeft } from "lucide-react";

export default function DashboardPage() {
  const [dashboardState, setDashboardState] = useState<DashboardState>("ready");
  const [cases] = useState<StructuredCase[]>(
    contractCasesData as StructuredCase[]
  );
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(
    contractCasesData[0]?.caseId || null
  );

  // Find currently selected case
  const selectedCase =
    cases.find((c) => c.caseId === selectedCaseId) || null;

  // Retry action from error state
  const handleRetry = () => {
    setDashboardState("loading");
    setTimeout(() => {
      setDashboardState("ready");
    }, 1200);
  };

  return (
    <div className="h-screen w-full bg-[#000000] text-white flex flex-col font-satoshi overflow-hidden">
      {/* Top Header */}
      <header className="h-16 border-b border-zinc-800 bg-[#0a0a0f]/90 backdrop-blur px-4 sm:px-6 flex items-center justify-between flex-shrink-0 z-20">
        {/* Left: Branding & Badge */}
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center hover:opacity-90 transition-opacity">
            <AiraLogo className="h-6 w-auto" />
          </Link>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#3954C0]/20 text-blue-300 font-medium border border-[#3954C0]/30">
            ER Staff Portal
          </span>
        </div>

        {/* Right: State Switcher & Back Link */}
        <div className="flex items-center space-x-3">
          {/* Dev State Switcher */}
          <StateSwitcher
            currentState={dashboardState}
            onStateChange={(st) => setDashboardState(st)}
          />

          {/* Back to Call Screen Link */}
          <Link
            href="/call"
            className="flex items-center space-x-1.5 text-xs font-medium text-zinc-300 hover:text-white transition-colors bg-zinc-900 hover:bg-zinc-800 px-3 py-1.5 rounded-lg border border-zinc-800"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Patient Call Screen</span>
            <span className="sm:hidden">Call</span>
          </Link>
        </div>
      </header>

      {/* Dashboard Body / State Machine Rendering */}
      <main className="flex-1 flex overflow-hidden relative">
        {dashboardState === "loading" && <LoadingState />}
        {dashboardState === "empty" && <EmptyState />}
        {dashboardState === "error" && <ErrorState onRetry={handleRetry} />}
        {dashboardState === "unauthorized" && <UnauthorizedState />}
        {dashboardState === "ready" && (
          <div className="flex-1 flex flex-col md:flex-row w-full h-full overflow-hidden">
            {/* Left Column: Case List */}
            <CaseList
              cases={cases}
              selectedCaseId={selectedCaseId}
              onSelectCase={(caseId) => setSelectedCaseId(caseId)}
            />

            {/* Right Column: Case Detail */}
            <CaseDetail caseItem={selectedCase} />
          </div>
        )}
      </main>
    </div>
  );
}
