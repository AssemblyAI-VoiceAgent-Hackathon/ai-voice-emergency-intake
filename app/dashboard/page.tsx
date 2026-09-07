"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { DashboardState } from "@/types/dashboard";
import { StructuredCase } from "@/types/structuredCase";
import { SYNTHETIC_CASES } from "@/lib/syntheticCases";
import {
  ROLE3_BASE,
  Role3Error,
  getCaseSnapshot,
  getHealth,
} from "@/lib/role3Client";
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
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [cases, setCases] = useState<StructuredCase[]>(SYNTHETIC_CASES);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(
    SYNTHETIC_CASES[0]?.caseId ?? null
  );
  const [liveCaseId, setLiveCaseId] = useState<string | null>(null);
  const [liveCaseInput, setLiveCaseInput] = useState("case_demo_001");
  const [reviewByCase, setReviewByCase] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);

  const selectedCase = useMemo(
    () => cases.find((item) => item.caseId === selectedCaseId) || null,
    [cases, selectedCaseId]
  );
  const live = Boolean(liveCaseId && selectedCaseId === liveCaseId);

  const resetSynthetic = () => {
    setCases(SYNTHETIC_CASES);
    setSelectedCaseId(SYNTHETIC_CASES[0]?.caseId ?? null);
    setLiveCaseId(null);
    setDashboardState("ready");
    setErrorMessage(undefined);
  };

  const handleRetry = () => {
    setDashboardState("loading");
    setTimeout(() => {
      resetSynthetic();
    }, 400);
  };

  const connectLive = async () => {
    const caseId = liveCaseInput.trim();
    if (!caseId) return;
    setConnecting(true);
    setDashboardState("loading");
    try {
      await getHealth();
      const snapshot = await getCaseSnapshot(caseId);
      if (!snapshot.structuredCase) {
        throw new Role3Error(
          404,
          "CASE_NOT_READY",
          "Role 3 has this case id but no structured case yet. Ingest from Role 2 first."
        );
      }
      setCases((prev) => {
        const without = prev.filter((item) => item.caseId !== caseId);
        return [snapshot.structuredCase as StructuredCase, ...without];
      });
      setSelectedCaseId(caseId);
      setLiveCaseId(caseId);
      setReviewByCase((prev) => ({ ...prev, [caseId]: snapshot.reviewStatus }));
      setDashboardState("ready");
      setErrorMessage(undefined);
    } catch (error) {
      if (error instanceof Role3Error && (error.status === 401 || error.status === 403)) {
        setDashboardState("unauthorized");
        setErrorMessage(error.message);
      } else if (error instanceof Role3Error && error.status === 404) {
        setDashboardState("error");
        setErrorMessage(
          `Case ${caseId} is not in Role 3 memory. Ingest a StructuredCase, then connect.`
        );
      } else {
        setDashboardState("error");
        setErrorMessage(
          error instanceof Error
            ? error.message
            : `Role 3 is not reachable at ${ROLE3_BASE}.`
        );
      }
    } finally {
      setConnecting(false);
    }
  };

  return (
    <div className="h-screen w-full bg-[#000000] text-white flex flex-col font-satoshi overflow-hidden">
      <header className="h-16 border-b border-zinc-800 bg-[#0a0a0f]/90 backdrop-blur px-4 sm:px-6 flex items-center justify-between flex-shrink-0 z-20">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center hover:opacity-90 transition-opacity">
            <AiraLogo className="h-6 w-auto" />
          </Link>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#3954C0]/20 text-blue-300 font-medium border border-[#3954C0]/30">
            ER Staff Portal
          </span>
          {live ? (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              Live Role 3
            </span>
          ) : (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
              Synthetic examples
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <form
            className="hidden md:flex items-center space-x-2"
            onSubmit={(event) => {
              event.preventDefault();
              void connectLive();
            }}
          >
            <input
              value={liveCaseInput}
              onChange={(event) => setLiveCaseInput(event.target.value)}
              placeholder="Role 3 caseId"
              className="w-40 bg-[#111116] border border-zinc-800 rounded-lg px-2.5 py-1.5 text-[11px] font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-[#3954C0]"
            />
            <button
              type="submit"
              disabled={connecting}
              className="text-[11px] font-semibold px-2.5 py-1.5 rounded-lg bg-[#3954C0] hover:bg-[#4a65d0] disabled:opacity-50"
            >
              {connecting ? "Connecting…" : "Connect"}
            </button>
            {liveCaseId && (
              <button
                type="button"
                onClick={resetSynthetic}
                className="text-[11px] font-semibold px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-700 hover:bg-zinc-800"
              >
                Synthetic
              </button>
            )}
          </form>

          <StateSwitcher
            currentState={dashboardState}
            onStateChange={(st) => setDashboardState(st)}
          />

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

      <main className="flex-1 flex overflow-hidden relative">
        {dashboardState === "loading" && <LoadingState />}
        {dashboardState === "empty" && <EmptyState />}
        {dashboardState === "error" && (
          <ErrorState onRetry={handleRetry} message={errorMessage} />
        )}
        {dashboardState === "unauthorized" && (
          <UnauthorizedState onRetry={resetSynthetic} message={errorMessage} />
        )}
        {dashboardState === "ready" && (
          <div className="flex-1 flex flex-col md:flex-row w-full h-full overflow-hidden">
            <CaseList
              cases={cases}
              selectedCaseId={selectedCaseId}
              onSelectCase={(caseId) => setSelectedCaseId(caseId)}
            />
            <CaseDetail
              caseItem={selectedCase}
              live={live}
              reviewStatus={selectedCaseId ? reviewByCase[selectedCaseId] : "none"}
              onCaseUpdate={(item, status) => {
                setCases((prev) =>
                  prev.map((entry) => (entry.caseId === item.caseId ? item : entry))
                );
                setReviewByCase((prev) => ({ ...prev, [item.caseId]: status }));
              }}
              onUnauthorized={(message) => {
                setErrorMessage(message);
                setDashboardState("unauthorized");
              }}
            />
          </div>
        )}
      </main>
    </div>
  );
}
