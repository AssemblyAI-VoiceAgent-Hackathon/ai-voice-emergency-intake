"use client";

import React, { useState, useEffect, useRef } from "react";
import { StructuredCase } from "@/types/structuredCase";
import { PendingEdit, StaffReviewPayload } from "@/types/staffReview";
import { startMockEventStream } from "@/lib/mockEventSimulator";
import { applyEdits } from "@/lib/applyEdits";
import {
  CaseEvent,
  Role3Error,
  getCaseSnapshot,
  lookupPatientAuthorised,
  submitStaffReview,
  subscribeCaseEvents,
} from "@/lib/role3Client";
import { ReviewSubmitResult } from "./ReviewActionForm";
import ProvenanceBadge from "./ProvenanceBadge";
import ConflictCard from "./ConflictCard";
import InformationGapItem from "./InformationGapItem";
import ReviewActionForm from "./ReviewActionForm";
import {
  Activity,
  AlertTriangle,
  Clock,
  User,
  FileText,
  ShieldAlert,
  HelpCircle,
  Stethoscope,
  Info,
  GitBranch,
  Layers,
  Sparkles,
  Pencil,
  Check,
  X,
} from "lucide-react";

interface CaseDetailProps {
  caseItem: StructuredCase | null;
  live?: boolean;
  reviewStatus?: string;
  onCaseUpdate?: (caseItem: StructuredCase, reviewStatus: string) => void;
  onUnauthorized?: (message: string) => void;
}

// ── Inline Edit Widget ────────────────────────────────────────────────────────
interface InlineEditProps {
  fieldLabel: string;
  currentValue: string | number;
  inputType?: "text" | "textarea" | "number";
  min?: number;
  max?: number;
  onConfirm: (value: string | number, reason: string) => void;
}

function InlineEdit({
  fieldLabel,
  currentValue,
  inputType = "text",
  min,
  max,
  onConfirm,
}: InlineEditProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<string>(String(currentValue));
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState(false);

  const handleConfirm = () => {
    if (!reason.trim()) {
      setReasonError(true);
      return;
    }
    const finalValue =
      inputType === "number" ? Number(draft) : draft;
    onConfirm(finalValue, reason.trim());
    setEditing(false);
    setReason("");
    setReasonError(false);
  };

  const handleCancel = () => {
    setEditing(false);
    setDraft(String(currentValue));
    setReason("");
    setReasonError(false);
  };

  if (!editing) {
    return (
      <button
        onClick={() => { setDraft(String(currentValue)); setEditing(true); }}
        className="inline-flex items-center space-x-1 text-[#a1a1aa] hover:text-blue-300 transition-colors group ml-1.5"
        title={`Edit ${fieldLabel}`}
      >
        <Pencil className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
      </button>
    );
  }

  return (
    <div className="mt-2 space-y-2 p-3 rounded-xl bg-[#0a0a0f] border border-[#3954C0]/40">
      <div className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold mb-1">
        Editing: {fieldLabel}
      </div>

      {inputType === "textarea" ? (
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          className="w-full bg-[#14161d] border border-white/10 rounded-lg px-3 py-2 text-[13px] text-white focus:outline-none focus:border-[#3954C0]/60 resize-none transition-colors"
          autoFocus
        />
      ) : (
        <input
          type={inputType}
          value={draft}
          min={min}
          max={max}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full bg-[#14161d] border border-white/10 rounded-lg px-3 py-2 text-[13px] text-white focus:outline-none focus:border-[#3954C0]/60 transition-colors"
          autoFocus
        />
      )}

      <div className="space-y-1">
        <label className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold">
          Reason for change <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={reason}
          onChange={(e) => { setReason(e.target.value); setReasonError(false); }}
          placeholder="Required — e.g. Confirmed by staff on arrival"
          className={`w-full bg-[#14161d] border rounded-lg px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none transition-colors ${
            reasonError
              ? "border-red-500/60 focus:border-red-500"
              : "border-white/10 focus:border-[#3954C0]/60"
          }`}
        />
        {reasonError && (
          <p className="text-[11px] text-red-400">Reason is required before confirming.</p>
        )}
      </div>

      <div className="flex items-center space-x-2 pt-1">
        <button
          onClick={handleConfirm}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#3954C0] text-white text-[12px] font-semibold hover:bg-[#4a65d0] transition-colors"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Confirm</span>
        </button>
        <button
          onClick={handleCancel}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#1a1d26] text-[#a1a1aa] text-[12px] font-semibold hover:text-white border border-white/10 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          <span>Cancel</span>
        </button>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CaseDetail({
  caseItem: initialCase,
  live = false,
  reviewStatus: initialReviewStatus = "none",
  onCaseUpdate,
  onUnauthorized,
}: CaseDetailProps) {
  const [displayedCase, setDisplayedCase] = useState<StructuredCase | null>(initialCase);
  const [selectedConflicts, setSelectedConflicts] = useState<Record<string, number>>({});
  const [pendingEdits, setPendingEdits] = useState<PendingEdit[]>([]);
  const [liveUpdateNotice, setLiveUpdateNotice] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState(initialReviewStatus);
  const [verifiedRecord, setVerifiedRecord] = useState<Record<string, unknown> | null>(null);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const seenEventIds = useRef<Set<string>>(new Set());
  const pendingEditsRef = useRef<PendingEdit[]>([]);
  pendingEditsRef.current = pendingEdits;

  const applyIncomingCase = (
    next: StructuredCase,
    status: string | undefined,
    notice: string
  ) => {
    setDisplayedCase((prev) => {
      if (prev && next.caseVersion < prev.caseVersion) return prev;
      const merged = applyEdits(next, pendingEditsRef.current);
      setLiveUpdateNotice(notice);
      window.setTimeout(() => setLiveUpdateNotice(null), 2500);
      if (status) setReviewStatus(status);
      onCaseUpdate?.(merged, status ?? reviewStatus);
      return merged;
    });
  };

  useEffect(() => {
    setDisplayedCase(initialCase);
    setSelectedConflicts({});
    setPendingEdits([]);
    setLiveUpdateNotice(null);
    setReviewStatus(initialReviewStatus);
    setVerifiedRecord(null);
    setToolStatus(null);
    seenEventIds.current.clear();
  }, [initialCase?.caseId, live]);

  useEffect(() => {
    if (!initialCase?.caseId) return;
    seenEventIds.current.clear();

    const handleEvent = (event: CaseEvent) => {
      if (seenEventIds.current.has(event.eventId)) return;
      seenEventIds.current.add(event.eventId);

      setDisplayedCase((prev) => {
        if (!prev) return null;
        if (event.caseVersion < prev.caseVersion) return prev;
        if (event.data?.structuredCase) {
          const merged = applyEdits(event.data.structuredCase, pendingEditsRef.current);
          setLiveUpdateNotice(`${event.eventType} (v${event.caseVersion})`);
          window.setTimeout(() => setLiveUpdateNotice(null), 2500);
          if (event.data.reviewStatus) setReviewStatus(event.data.reviewStatus);
          onCaseUpdate?.(merged, event.data.reviewStatus ?? reviewStatus);
          return { ...merged, caseVersion: event.caseVersion };
        }
        if (event.eventType === "case.review_status") {
          if (event.data.reviewStatus) setReviewStatus(event.data.reviewStatus);
          setLiveUpdateNotice(`Review: ${event.data.reviewStatus ?? event.data.action}`);
          window.setTimeout(() => setLiveUpdateNotice(null), 2500);
          return { ...prev, caseVersion: Math.max(prev.caseVersion, event.caseVersion) };
        }
        if (event.eventType === "case.tool_status") {
          setToolStatus(`${event.data.tool ?? "tool"}: ${event.data.status ?? "update"}`);
          return prev;
        }
        if (event.caseVersion > prev.caseVersion) {
          return { ...prev, caseVersion: event.caseVersion };
        }
        return prev;
      });
    };

    if (live) {
      return subscribeCaseEvents(initialCase.caseId, handleEvent, (error) => {
        if (error.status === 401 || error.status === 403) {
          onUnauthorized?.(error.message);
        }
      });
    }

    return startMockEventStream(initialCase.caseId, handleEvent, initialCase.caseVersion);
  }, [initialCase?.caseId, live]);

  useEffect(() => {
    if (!live || !initialCase?.subject?.patientReference) {
      setVerifiedRecord(null);
      return;
    }
    let cancelled = false;
    lookupPatientAuthorised({ patientPublicId: initialCase.subject.patientReference })
      .then((record) => {
        if (!cancelled) setVerifiedRecord(record);
      })
      .catch(() => {
        if (!cancelled) setVerifiedRecord(null);
      });
    return () => {
      cancelled = true;
    };
  }, [live, initialCase?.caseId, initialCase?.subject?.patientReference]);

  const handleRefreshCase = async () => {
    if (!initialCase?.caseId) return;
    if (!live) {
      setDisplayedCase((prev) => (prev ? { ...prev } : prev));
      return;
    }
    try {
      const snapshot = await getCaseSnapshot(initialCase.caseId);
      if (snapshot.structuredCase) {
        applyIncomingCase(
          snapshot.structuredCase,
          snapshot.reviewStatus,
          `Refreshed from Role 3 (v${snapshot.caseVersion})`
        );
      }
    } catch (error) {
      if (error instanceof Role3Error && (error.status === 401 || error.status === 403)) {
        onUnauthorized?.(error.message);
      }
    }
  };

  const handleReviewSubmit = async (
    payload: StaffReviewPayload
  ): Promise<ReviewSubmitResult> => {
    if (!live) {
      return { ok: true, message: "Synthetic review accepted. Connect Role 3 to save via Role 4." };
    }
    try {
      const result = await submitStaffReview(payload);
      if (result.caseVersion !== undefined) {
        setDisplayedCase((prev) =>
          prev ? { ...prev, caseVersion: result.caseVersion as number } : prev
        );
      }
      if (result.status) setReviewStatus(result.status === "approve" ? "approved" : result.status);
      const extra =
        result.approvedRecord?.approvedRecordPublicId
          ? ` Saved ${result.approvedRecord.approvedRecordPublicId}.`
          : "";
      return { ok: true, message: `Role 3 accepted ${result.status}.${extra}` };
    } catch (error) {
      if (error instanceof Role3Error && error.status === 409) {
        return {
          ok: false,
          conflictVersion: error.latestCaseVersion,
          message: error.message,
        };
      }
      if (error instanceof Role3Error && (error.status === 401 || error.status === 403)) {
        onUnauthorized?.(error.message);
        return { ok: false, unauthorized: true, message: error.message };
      }
      return {
        ok: false,
        message: error instanceof Error ? error.message : "Review submission failed.",
      };
    }
  };

  if (!displayedCase) {
    return (
      <section className="flex-1 bg-[#0a0a0f] flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-[#14161d] border border-white/10 flex items-center justify-center mb-4 text-[#3954C0]">
          <Activity className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-white mb-2">No Case Selected</h3>
        <p className="text-[#a1a1aa] text-xs max-w-sm leading-relaxed">
          Select a case from the list on the left to review chief complaints, symptoms, observations, and structured contract data.
        </p>
      </section>
    );
  }

  const patientLabel =
    displayedCase.subject.patientReference || displayedCase.caseId;

  const handleConflictSelect = (fieldPath: string, valueIndex: number) => {
    setSelectedConflicts((prev) => ({
      ...prev,
      [fieldPath]: valueIndex,
    }));
  };

  // Helper: push a new edit, replacing any existing edit for the same path
  const pushEdit = (
    path: string,
    value: string | number,
    reason: string,
    forcedOp?: "add" | "replace"
  ) => {
    let op: "add" | "replace" = forcedOp ?? "replace";
    if (!forcedOp && displayedCase) {
      const parts = path.split("/").filter(Boolean);
      let current: any = displayedCase;
      for (const part of parts) {
        if (current && typeof current === "object" && part in current) {
          current = current[part];
        } else {
          current = undefined;
          break;
        }
      }
      if (Array.isArray(current)) {
        op = current.length === 0 ? "add" : "replace";
      }
    }

    setPendingEdits((prev) => {
      const without = prev.filter((e) => e.path !== path);
      return [...without, { op, path, value, reason }];
    });
  };

  return (
    <section className="flex-1 bg-[#0a0a0f] flex flex-col h-full overflow-y-auto custom-scrollbar text-white">
      {/* ── Header Banner ───────────────────────────────────────────────────── */}
      <div className="p-6 border-b border-white/10 bg-[#14161d] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-[#3954C0]/20 border border-[#3954C0]/40 flex items-center justify-center text-[#3954C0]">
              <User className="w-6 h-6 text-blue-300" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                  {patientLabel}
                </h2>
                <span className="text-[11px] px-2.5 py-0.5 rounded bg-[#1a1d26] text-zinc-300 font-mono border border-white/10">
                  {displayedCase.caseId}
                </span>
              </div>
              <p className="text-[13px] text-[#a1a1aa] flex items-center space-x-3 mt-1 font-normal">
                <span>
                  Sex: <strong className="text-white capitalize font-semibold">{displayedCase.subject.sexAtBirth}</strong>
                </span>
                <span>•</span>
                <span>
                  Age: <strong className="text-white font-semibold">{displayedCase.subject.ageYears ?? "N/A"}</strong>
                </span>
                <span>•</span>
                <span>
                  Language: <strong className="text-white font-semibold">{displayedCase.language}</strong>
                </span>
                <span>•</span>
                <span className="flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-[#a1a1aa]" />
                  <span>Captured {new Date(displayedCase.capturedAt).toLocaleString()}</span>
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {toolStatus && (
              <span className="px-3 py-1 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700 text-[11px] font-semibold">
                {toolStatus}
              </span>
            )}
            {liveUpdateNotice && (
              <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40 text-[11px] font-semibold animate-pulse shadow-sm">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                <span>{liveUpdateNotice}</span>
              </span>
            )}
            <span
              className={`
                px-3.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border shadow-sm
                ${
                  displayedCase.status === "ready_for_review"
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                    : displayedCase.status === "needs_information"
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                    : "bg-[#3954C0]/20 text-blue-300 border-[#3954C0]/50"
                }
              `}
            >
              {displayedCase.status.replace(/_/g, " ")}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1 text-[13px] text-[#a1a1aa]">
          <span className="text-[#8b8d98] font-medium text-[11px] uppercase tracking-wider">Informants:</span>
          {displayedCase.informants.map((inf, idx) => (
            <span key={idx} className="px-2.5 py-0.5 rounded bg-[#1a1d26] text-white border border-white/10 capitalize text-xs">
              {inf}
            </span>
          ))}
          <span className="text-[#8b8d98] ml-2 text-[11px] uppercase tracking-wider">Session:</span>
          <span className="font-mono text-zinc-300 text-xs">{displayedCase.sessionId}</span>
          <span className="text-[#8b8d98] ml-2 text-[11px] uppercase tracking-wider">Version:</span>
          <span className="font-mono text-zinc-300 text-xs">v{displayedCase.caseVersion}</span>
        </div>
      </div>

      {/* ── Main Content ─────────────────────────────────────────────────────── */}
      <div className="p-6 space-y-6 flex-1">

        {live && verifiedRecord && (
          <div className="bg-[#14161d] border-l-[3px] border-l-emerald-500 border border-white/10 rounded-2xl p-5 space-y-2">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-emerald-400">
              Verified record (Role 4 via Role 3)
            </h3>
            <pre className="text-[11px] font-mono text-zinc-300 whitespace-pre-wrap break-all">
              {JSON.stringify(verifiedRecord, null, 2)}
            </pre>
          </div>
        )}

        {/* Conflicts */}
        {displayedCase.conflicts && displayedCase.conflicts.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-amber-400 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Interactive Data Conflicts ({displayedCase.conflicts.length})</span>
            </h3>
            <div className="space-y-3">
              {displayedCase.conflicts.map((conf) => (
                <ConflictCard
                  key={conf.fieldPath}
                  conflict={conf}
                  selectedIndex={selectedConflicts[conf.fieldPath] ?? null}
                  onSelectValue={(valIdx) => handleConflictSelect(conf.fieldPath, valIdx)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Information Gaps */}
        {displayedCase.informationGaps && displayedCase.informationGaps.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-amber-400 flex items-center space-x-2">
              <HelpCircle className="w-4 h-4 text-amber-400" />
              <span>Information Gaps ({displayedCase.informationGaps.length})</span>
            </h3>
            <div className="space-y-2">
              {displayedCase.informationGaps.map((gap, idx) => {
                const isResolved = pendingEdits.some(
                  (e) => e.path === gap.fieldPath
                );
                return (
                  <InformationGapItem
                    key={idx}
                    gap={gap}
                    isResolved={isResolved}
                    onResolve={(value, reason) =>
                      pushEdit(gap.fieldPath, value, reason)
                    }
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Case Summary */}
        <div className="bg-[#14161d] border-l-[3px] border-l-[#3954C0] border border-white/10 rounded-2xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] flex items-center space-x-2">
              <FileText className="w-4 h-4 text-[#3954C0]" />
              <span>Case Summary</span>
            </h3>
          </div>
          <div className="text-[15px] sm:text-[16px] font-semibold text-blue-200 bg-[#3954C0]/15 border border-[#3954C0]/35 p-3.5 rounded-xl">
            {displayedCase.summary.oneLine}
          </div>
          <p className="text-[15px] sm:text-[16px] text-white leading-relaxed font-normal bg-[#1a1d26] p-4 rounded-xl border border-white/10">
            {displayedCase.summary.narrative}
          </p>
        </div>

        {/* Safety Signals */}
        {displayedCase.safetySignals && displayedCase.safetySignals.length > 0 && (
          <div className="bg-[#14161d] border-l-[3px] border-l-[#FF3714] border border-[#FF3714]/30 rounded-2xl p-5 shadow-lg space-y-3">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#FF3714] flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-[#FF3714]" />
              <span>Safety Signals ({displayedCase.safetySignals.length})</span>
            </h3>
            <div className="space-y-2">
              {displayedCase.safetySignals.map((sig, idx) => (
                <div key={idx} className="flex items-center justify-between p-3.5 rounded-xl bg-[#1a1d26] border border-red-500/30">
                  <div>
                    <span className="text-[16px] font-semibold text-red-200">{sig.label}</span>
                    <span className="ml-2 font-mono text-[11px] text-[#a1a1aa]">({sig.code})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] px-2.5 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 font-bold uppercase tracking-wider">
                      {sig.status}
                    </span>
                    {sig.evidenceSourceRefs.map((ref, rIdx) => (
                      <span key={rIdx} className="text-[11px] font-mono text-zinc-300 bg-[#0a0a0f] px-2 py-0.5 rounded border border-white/10">
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Chief Complaint (EDITABLE) ──────────────────────────────────────── */}
        <div className="bg-[#14161d] border-l-[3px] border-l-[#3954C0] border border-white/10 rounded-2xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] flex items-center space-x-2">
              <Stethoscope className="w-4 h-4 text-[#3954C0]" />
              <span>Chief Complaint</span>
            </h3>
            <ProvenanceBadge
              fieldPath="/chiefComplaint/text"
              provenanceList={displayedCase.provenance}
            />
          </div>

          <div className="p-4 rounded-xl bg-[#1a1d26] border border-white/10 space-y-2">
            <div className="flex items-start space-x-1">
              <p className="text-[17px] sm:text-[18px] font-semibold text-white leading-snug flex-1">
                {/* Show current value (may have been overridden by a pending edit) */}
                {(() => {
                  const override = pendingEdits.find(e => e.path === "/chiefComplaint/text");
                  return override ? String(override.value) : displayedCase.chiefComplaint.text;
                })()}
              </p>
              <InlineEdit
                fieldLabel="Chief Complaint"
                currentValue={displayedCase.chiefComplaint.text}
                inputType="textarea"
                onConfirm={(value, reason) =>
                  pushEdit("/chiefComplaint/text", value, reason)
                }
              />
            </div>
            {displayedCase.chiefComplaint.onsetText && (
              <p className="text-[13px] text-[#a1a1aa] font-normal">
                Onset: <span className="text-zinc-200 font-medium">{displayedCase.chiefComplaint.onsetText}</span>
              </p>
            )}
            <div className="flex items-center space-x-1.5 pt-1">
              <span className="text-[11px] text-[#8b8d98] font-medium uppercase tracking-wider">Sources:</span>
              {displayedCase.chiefComplaint.sourceRefs.map((sr, idx) => (
                <span key={idx} className="text-[11px] font-mono bg-[#0a0a0f] text-zinc-300 px-2 py-0.5 rounded border border-white/10">
                  {sr}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ── Reported Symptoms (severity EDITABLE) ─────────────────────────── */}
        <div className="bg-[#14161d] border-l-[3px] border-l-[#3954C0] border border-white/10 rounded-2xl p-5 shadow-lg space-y-3">
          <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] flex items-center space-x-2">
            <Activity className="w-4 h-4 text-[#3954C0]" />
            <span>Reported Symptoms ({displayedCase.symptoms.length})</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {displayedCase.symptoms.map((sym, idx) => {
              const severityPath = `/symptoms/${idx}/severity0To10`;
              const overriddenSeverity = pendingEdits.find(e => e.path === severityPath);
              const displaySeverity = overriddenSeverity
                ? Number(overriddenSeverity.value)
                : sym.severity0To10;

              return (
                <div key={idx} className="p-4 rounded-xl bg-[#1a1d26] border border-white/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[16px] font-semibold text-white capitalize">{sym.name}</span>
                    {displaySeverity !== null && (
                      <div className="flex items-center space-x-1">
                        <span className="text-[11px] px-2.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold border border-blue-500/30">
                          Severity: {displaySeverity}/10
                        </span>
                        <InlineEdit
                          fieldLabel={`${sym.name} Severity`}
                          currentValue={sym.severity0To10 ?? 0}
                          inputType="number"
                          min={0}
                          max={10}
                          onConfirm={(value, reason) =>
                            pushEdit(severityPath, value, reason)
                          }
                        />
                      </div>
                    )}
                  </div>
                  <div className="text-[13px] text-[#a1a1aa] space-y-1 font-normal">
                    {sym.location && <div>Location: <span className="text-zinc-200 font-medium">{sym.location}</span></div>}
                    {sym.onsetText && <div>Onset: <span className="text-zinc-200 font-medium">{sym.onsetText}</span></div>}
                    {sym.notes && <div className="italic text-zinc-300">&quot;{sym.notes}&quot;</div>}
                  </div>
                  <div className="flex items-center space-x-1.5 pt-1">
                    {sym.sourceRefs.map((sr, sIdx) => (
                      <span key={sIdx} className="text-[11px] font-mono bg-[#0a0a0f] text-zinc-300 px-2 py-0.5 rounded border border-white/10">
                        {sr}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Clinical Observations */}
        {displayedCase.observations && displayedCase.observations.length > 0 && (
          <div className="bg-[#14161d] border-l-[3px] border-l-[#3954C0] border border-white/10 rounded-2xl p-5 shadow-lg space-y-3">
            <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] flex items-center space-x-2">
              <Layers className="w-4 h-4 text-[#3954C0]" />
              <span>Clinical Observations ({displayedCase.observations.length})</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {displayedCase.observations.map((obs, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-[#1a1d26] border border-white/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] text-[#a1a1aa] font-medium uppercase tracking-wider capitalize">{obs.name.replace("_", " ")}</span>
                    <ProvenanceBadge
                      fieldPath={`/observations/${idx}/value`}
                      provenanceList={displayedCase.provenance}
                    />
                  </div>
                  <div className="text-[18px] sm:text-[20px] font-bold text-white">
                    {obs.value} <span className="text-[13px] font-normal text-[#a1a1aa]">{obs.unit}</span>
                  </div>
                  <div className="flex justify-between items-center text-[13px] text-[#a1a1aa] pt-1">
                    <span>Origin: <strong className="text-zinc-200 capitalize font-medium">{obs.origin}</strong></span>
                    <span>{new Date(obs.observedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Medical History (status EDITABLE) ─────────────────────────────── */}
        <div className="bg-[#14161d] border-l-[3px] border-l-[#575757] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
          <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] flex items-center space-x-2">
            <Info className="w-4 h-4 text-[#575757]" />
            <span>Medical History</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Conditions */}
            <div className="p-4 rounded-xl bg-[#1a1d26] border border-white/10 space-y-2.5">
              <div className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98]">
                Conditions ({displayedCase.history.conditions.length})
              </div>
              {displayedCase.history.conditions.length === 0 ? (
                <div className="text-[13px] text-[#a1a1aa] italic">None reported</div>
              ) : (
                displayedCase.history.conditions.map((cond, idx) => {
                  const path = `/history/conditions/${idx}/status`;
                  const override = pendingEdits.find(e => e.path === path);
                  return (
                    <div key={idx} className="text-xs bg-[#0a0a0f] p-3 rounded-lg border border-white/10 space-y-1">
                      <div className="text-[15px] font-semibold text-white capitalize">{cond.name}</div>
                      <div className="flex items-center space-x-1 text-[13px] text-[#a1a1aa] capitalize">
                        <span>Status: <span className="text-zinc-200">{override ? String(override.value) : cond.status}</span></span>
                        <InlineEdit
                          fieldLabel={`${cond.name} status`}
                          currentValue={cond.status}
                          inputType="text"
                          onConfirm={(value, reason) => pushEdit(path, value, reason)}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Medications */}
            <div className="p-4 rounded-xl bg-[#1a1d26] border border-white/10 space-y-2.5">
              <div className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98]">
                Medications ({displayedCase.history.medications.length})
              </div>
              {displayedCase.history.medications.length === 0 ? (
                <div className="text-[13px] text-[#a1a1aa] italic">None reported / incomplete</div>
              ) : (
                displayedCase.history.medications.map((med, idx) => {
                  const path = `/history/medications/${idx}/status`;
                  const override = pendingEdits.find(e => e.path === path);
                  return (
                    <div key={idx} className="text-xs bg-[#0a0a0f] p-3 rounded-lg border border-white/10 space-y-1">
                      <div className="text-[15px] font-semibold text-white capitalize">{med.name}</div>
                      <div className="flex items-center space-x-1 text-[13px] text-[#a1a1aa] capitalize">
                        <span>Status: <span className="text-zinc-200">{override ? String(override.value) : med.status}</span></span>
                        <InlineEdit
                          fieldLabel={`${med.name} status`}
                          currentValue={med.status}
                          inputType="text"
                          onConfirm={(value, reason) => pushEdit(path, value, reason)}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Allergies */}
            <div className="p-4 rounded-xl bg-[#1a1d26] border border-white/10 space-y-2.5">
              <div className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98]">
                Allergies ({displayedCase.history.allergies.length})
              </div>
              {displayedCase.history.allergies.length === 0 ? (
                <div className="text-[13px] text-[#a1a1aa] italic">None reported</div>
              ) : (
                displayedCase.history.allergies.map((all, idx) => {
                  const path = `/history/allergies/${idx}/status`;
                  const override = pendingEdits.find(e => e.path === path);
                  return (
                    <div key={idx} className="text-xs bg-[#0a0a0f] p-3 rounded-lg border border-white/10 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[15px] font-semibold text-white capitalize">{all.name}</span>
                        <ProvenanceBadge
                          fieldPath={`/history/allergies/${idx}/status`}
                          provenanceList={displayedCase.provenance}
                        />
                      </div>
                      <div className="flex items-center space-x-1 text-[13px] text-[#a1a1aa] capitalize">
                        <span>Status: <strong className="text-zinc-200">{override ? String(override.value) : all.status}</strong></span>
                        <InlineEdit
                          fieldLabel={`${all.name} allergy status`}
                          currentValue={all.status}
                          inputType="text"
                          onConfirm={(value, reason) => pushEdit(path, value, reason)}
                        />
                      </div>
                      {all.details && (
                        <div className="text-[13px] text-amber-300 italic">&quot;{all.details}&quot;</div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* AI Metadata Footer */}
        <div className="p-4 rounded-xl bg-[#14161d] border border-white/10 text-[13px] text-[#a1a1aa] flex flex-wrap justify-between items-center gap-2">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-[#3954C0]" />
            <span>AI Model: <strong className="text-white font-medium">{displayedCase.extractionMetadata.model}</strong></span>
            <span>•</span>
            <span>Prompt: <strong className="text-white font-medium">{displayedCase.extractionMetadata.promptVersion}</strong></span>
          </div>
          <div className="flex items-center space-x-2 font-mono text-[11px]">
            <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
            <span>Completed: {new Date(displayedCase.extractionMetadata.completedAt).toLocaleTimeString()}</span>
          </div>
        </div>

        {/* ── Staff Review Action Form ─────────────────────────────────────────── */}
        {/* key={caseId} forces full remount on case switch — fixes Bug 1 */}
        <ReviewActionForm
          key={displayedCase.caseId}
          caseItem={displayedCase}
          pendingEdits={pendingEdits}
          setPendingEdits={setPendingEdits}
          live={live}
          reviewStatus={reviewStatus}
          onRefreshCase={handleRefreshCase}
          onSubmit={handleReviewSubmit}
        />

      </div>
    </section>
  );
}
