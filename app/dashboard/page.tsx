"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { DashboardState } from "@/types/dashboard";
import { StructuredCase } from "@/types/structuredCase";
import { SYNTHETIC_CASES } from "@/lib/syntheticCases";
import {
  ROLE3_BASE,
  Role3Error,
  getCaseSnapshot,
  getHealth,
  listCases,
} from "@/lib/role3Client";
import CaseList from "@/components/dashboard/CaseList";
import CaseDetail from "@/components/dashboard/CaseDetail";
import LoadingState from "@/components/dashboard/LoadingState";
import EmptyState from "@/components/dashboard/EmptyState";
import ErrorState from "@/components/dashboard/ErrorState";
import UnauthorizedState from "@/components/dashboard/UnauthorizedState";
import AiraLogo from "@/components/AiraLogo";
import { ArrowLeft } from "lucide-react";

export default function DashboardPage() {
  const [dashboardState, setDashboardState] = useState<DashboardState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | undefined>();
  const [cases, setCases] = useState<StructuredCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [liveIds, setLiveIds] = useState<string[]>([]);
  const [liveCaseInput, setLiveCaseInput] = useState("");
  const [incomingCaseId, setIncomingCaseId] = useState<string | null>(null);
  const [reviewByCase, setReviewByCase] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);

  const selectedCase = useMemo(
    () => cases.find((item) => item.caseId === selectedCaseId) || null,
    [cases, selectedCaseId]
  );
  const live = Boolean(selectedCaseId && liveIds.includes(selectedCaseId));

  const resetSynthetic = () => {
    setCases(SYNTHETIC_CASES);
    setSelectedCaseId(SYNTHETIC_CASES[0]?.caseId ?? null);
    setLiveIds([]);
    setDashboardState("ready");
    setErrorMessage(undefined);
  };

  const handleRetry = () => {
    const wanted = new URLSearchParams(window.location.search).get("caseId");
    setDashboardState("loading");
    void bootstrapLive(wanted);
  };

  const applyLiveSnapshots = (
    snapshots: Awaited<ReturnType<typeof getCaseSnapshot>>[],
    preferredId: string | null
  ) => {
    const liveCases = snapshots
      .map((snapshot) => snapshot.structuredCase)
      .filter((item): item is StructuredCase => Boolean(item));
    if (!liveCases.length) return false;
    setCases(liveCases);
    setLiveIds(liveCases.map((item) => item.caseId));
    setSelectedCaseId((current) => {
      if (preferredId && liveCases.some((item) => item.caseId === preferredId)) {
        return preferredId;
      }
      if (current && liveCases.some((item) => item.caseId === current)) {
        return current;
      }
      return liveCases[0].caseId;
    });
    const select =
      (preferredId && liveCases.some((item) => item.caseId === preferredId)
        ? preferredId
        : liveCases[0].caseId) ?? null;
    if (select) setLiveCaseInput(select);
    const reviews: Record<string, string> = {};
    for (const snapshot of snapshots) {
      if (snapshot.structuredCase) reviews[snapshot.caseId] = snapshot.reviewStatus;
    }
    setReviewByCase(reviews);
    setDashboardState("ready");
    setErrorMessage(undefined);
    return true;
  };

  const bootstrapLive = async (wanted: string | null, silent = false) => {
    if (!silent) setConnecting(true);
    try {
      await getHealth();
      const listed = await listCases();
      const ids = listed.map((item) => item.caseId);
      if (wanted && !ids.includes(wanted)) ids.unshift(wanted);
      if (!ids.length) {
        if (!silent) {
          setCases([]);
          setLiveIds([]);
          setSelectedCaseId(null);
          setDashboardState("empty");
        }
        return;
      }
      if (!silent) setDashboardState("loading");
      const snapshots = await Promise.all(
        ids.map((id) =>
          getCaseSnapshot(id).catch((error) => {
            if (!silent && wanted && id === wanted) throw error;
            return null;
          })
        )
      );
      const ready = snapshots.filter((item): item is NonNullable<typeof item> => Boolean(item));
      if (!applyLiveSnapshots(ready, wanted) && !silent && wanted) {
        throw new Role3Error(
          404,
          "CASE_NOT_READY",
          `Case ${wanted} is not in Role 3 yet. Finish a call or send a demo intake first.`
        );
      }
    } catch (error) {
      if (silent) return;
      if (error instanceof Role3Error && (error.status === 401 || error.status === 403)) {
        setDashboardState("unauthorized");
        setErrorMessage(error.message);
      } else {
        setDashboardState("error");
        setErrorMessage(
          error instanceof Error
            ? error.message
            : `Role 3 is not reachable at ${ROLE3_BASE}.`
        );
      }
    } finally {
      if (!silent) setConnecting(false);
    }
  };

  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("caseId");
    if (wanted) setIncomingCaseId(wanted);
    void bootstrapLive(wanted);
    const timer = window.setInterval(() => {
      void bootstrapLive(wanted, true);
    }, 3000);
    return () => window.clearInterval(timer);
    // Live Role 3 is the default Role 5 view.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      applyLiveSnapshots([snapshot], caseId);
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
              Live intake
            </span>
          ) : (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
              Examples
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
              placeholder="Case id"
              className="w-40 bg-[#111116] border border-zinc-800 rounded-lg px-2.5 py-1.5 text-[11px] font-mono text-white placeholder-zinc-500 focus:outline-none focus:border-[#3954C0]"
            />
            <button
              type="submit"
              disabled={connecting}
              className="text-[11px] font-semibold px-2.5 py-1.5 rounded-lg bg-[#3954C0] hover:bg-[#4a65d0] disabled:opacity-50"
            >
              {connecting ? "Connecting…" : "Connect"}
            </button>
            {liveIds.length > 0 ? (
              <button
                type="button"
                onClick={resetSynthetic}
                className="text-[11px] font-semibold px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-700 hover:bg-zinc-800"
              >
                Synthetic
              </button>
            ) : (
              <button
                type="button"
                onClick={handleRetry}
                className="text-[11px] font-semibold px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-700 hover:bg-zinc-800"
              >
                Refresh live
              </button>
            )}
          </form>

          <Link
            href="/call"
            className="flex items-center space-x-1.5 text-xs font-medium text-zinc-300 hover:text-white transition-colors bg-zinc-900 hover:bg-zinc-800 px-3 py-1.5 rounded-lg border border-zinc-800"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Patient call</span>
            <span className="sm:hidden">Call</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden relative">
        {incomingCaseId && dashboardState === "ready" && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 px-4 py-2 rounded-full bg-emerald-500/15 border border-emerald-400/30 text-emerald-200 text-[12px] font-medium">
            New voice intake received
          </div>
        )}
        {dashboardState === "loading" && <LoadingState />}
        {dashboardState === "empty" && <EmptyState />}
        {dashboardState === "error" && (
          <ErrorState onRetry={handleRetry} message={errorMessage} />
        )}
        {dashboardState === "unauthorized" && (
          <UnauthorizedState onRetry={handleRetry} message={errorMessage} />
        )}
        {dashboardState === "ready" && (
          <div className="flex-1 flex flex-col md:flex-row w-full h-full overflow-hidden">
            <CaseList
              cases={cases}
              selectedCaseId={selectedCaseId}
              incomingCaseId={incomingCaseId}
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
