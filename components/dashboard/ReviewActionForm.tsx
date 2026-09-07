"use client";

import React, { useState, useCallback } from "react";
import { StructuredCase } from "@/types/structuredCase";
import {
  PendingEdit,
  ReviewAction,
  FinalTriage,
  StaffReviewPayload,
} from "@/types/staffReview";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  MessageSquarePlus,
  Plus,
  RefreshCw,
  Send,
  ThumbsUp,
  Trash2,
  X,
} from "lucide-react";

interface ReviewActionFormProps {
  caseItem: StructuredCase;
  pendingEdits: PendingEdit[];
  setPendingEdits: React.Dispatch<React.SetStateAction<PendingEdit[]>>;
  onRefreshCase?: (newVersion: number) => void;
  onSubmit?: (payload: StaffReviewPayload) => void;
}

function generateIdempotencyKey(caseId: string, version: number): string {
  return `review-${caseId}-v${version}-${Date.now()}`;
}

export default function ReviewActionForm({
  caseItem,
  pendingEdits,
  setPendingEdits,
  onRefreshCase,
  onSubmit,
}: ReviewActionFormProps) {
  const [selectedAction, setSelectedAction] = useState<ReviewAction>(null);
  const [informationRequestQuestions, setInformationRequestQuestions] =
    useState<string[]>([""]);
  const [finalTriage, setFinalTriage] = useState<FinalTriage>({
    code: "",
    label: "",
    rationale: "",
  });
  const [comment, setComment] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [conflictError, setConflictError] = useState<{
    currentServerVersion: number;
  } | null>(null);

  // ── Bug 2: unresolved required gaps computation ────────────────────────────
  // Re-derives on every render since pendingEdits is a prop that changes.
  const unresolvedRequiredGaps = (caseItem.informationGaps ?? []).filter(
    (gap) =>
      gap.priority === "required" &&
      !pendingEdits.some((e) => e.path === gap.fieldPath)
  );

  // ── Validation ──────────────────────────────────────────────────────────────
  const canSubmit = useCallback((): boolean => {
    if (!selectedAction) return false;
    if (selectedAction === "approve") {
      // Must have triage code + label
      if (!finalTriage.code.trim() || !finalTriage.label.trim()) return false;
      // Bug 2: must resolve all required gaps before approving
      if (unresolvedRequiredGaps.length > 0) return false;
    }
    if (
      selectedAction === "request_more_information" &&
      informationRequestQuestions.filter((q) => q.trim()).length === 0
    )
      return false;
    return true;
  }, [selectedAction, finalTriage, informationRequestQuestions, unresolvedRequiredGaps]);

  // ── Payload builder ──────────────────────────────────────────────────────────
  const buildPayload = useCallback((): StaffReviewPayload | null => {
    if (!selectedAction) return null;
    return {
      schemaVersion: "1.0.0",
      caseId: caseItem.caseId,
      baseCaseVersion: caseItem.caseVersion,
      idempotencyKey: generateIdempotencyKey(caseItem.caseId, caseItem.caseVersion),
      action: selectedAction,
      edits: pendingEdits,
      informationRequest:
        selectedAction === "request_more_information"
          ? {
              questions: informationRequestQuestions.filter((q) => q.trim()),
            }
          : null,
      finalTriage:
        selectedAction === "approve"
          ? {
              code: finalTriage.code.trim(),
              label: finalTriage.label.trim(),
              rationale: finalTriage.rationale.trim() || null!,
            }
          : null,
      comment: comment.trim() || null,
    };
  }, [
    selectedAction,
    caseItem,
    pendingEdits,
    informationRequestQuestions,
    finalTriage,
    comment,
  ]);

  // ── Submit ───────────────────────────────────────────────────────────────────
  const handleSubmit = () => {
    const payload = buildPayload();
    if (!payload) return;

    // STEP 3: 30% chance of simulated 409 conflict
    const isConflict = Math.random() < 0.3;

    if (isConflict) {
      const currentServerVersion = caseItem.caseVersion + 1;
      const mock409Error = {
        error: {
          code: "CASE_VERSION_CONFLICT",
          message: "The submitted case version is stale.",
          fieldErrors: [
            {
              path: "/caseVersion",
              message: `Expected version ${currentServerVersion}`,
            },
          ],
        },
      };
      console.warn("[Aira] Simulated 409 Conflict Response:", mock409Error);

      // Preserve form state and pendingEdits, show conflict banner
      setConflictError({ currentServerVersion });
      setSubmitted(false);
      return;
    }

    // 70% success path
    console.log("[Aira] Staff review payload (mock):", JSON.stringify(payload, null, 2));
    onSubmit?.(payload);
    setConflictError(null);
    setPendingEdits([]); // Clear queued edits on success
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3500);
  };

  const handleRefresh = () => {
    if (conflictError && onRefreshCase) {
      onRefreshCase(conflictError.currentServerVersion);
    }
    setConflictError(null);
  };

  // ── Questions helpers ────────────────────────────────────────────────────────
  const addQuestion = () => {
    if (informationRequestQuestions.length < 10) {
      setInformationRequestQuestions((prev) => [...prev, ""]);
    }
  };

  const removeQuestion = (idx: number) => {
    setInformationRequestQuestions((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateQuestion = (idx: number, val: string) => {
    setInformationRequestQuestions((prev) => {
      const next = [...prev];
      next[idx] = val;
      return next;
    });
  };

  const removeEdit = (idx: number) => {
    setPendingEdits((prev) => prev.filter((_, i) => i !== idx));
  };

  const previewPayload = buildPayload();

  // ── Action pill config ───────────────────────────────────────────────────────
  const actions: {
    value: Exclude<ReviewAction, null>;
    label: string;
    icon: React.ReactNode;
    activeClass: string;
    inactiveClass: string;
  }[] = [
    {
      value: "save_draft",
      label: "Save Draft",
      icon: <ClipboardCheck className="w-4 h-4" />,
      activeClass:
        "bg-[#2a2d3a] text-white border-[#5a5d6e]",
      inactiveClass:
        "bg-transparent text-[#a1a1aa] border-white/10 hover:border-white/25 hover:text-white",
    },
    {
      value: "request_more_information",
      label: "Request Info",
      icon: <MessageSquarePlus className="w-4 h-4" />,
      activeClass:
        "bg-amber-500/20 text-amber-300 border-amber-500/60",
      inactiveClass:
        "bg-transparent text-[#a1a1aa] border-white/10 hover:border-amber-500/40 hover:text-amber-300",
    },
    {
      value: "approve",
      label: "Approve",
      icon: <ThumbsUp className="w-4 h-4" />,
      activeClass:
        "bg-emerald-500/20 text-emerald-300 border-emerald-500/60",
      inactiveClass:
        "bg-transparent text-[#a1a1aa] border-white/10 hover:border-emerald-500/40 hover:text-emerald-300",
    },
  ];

  return (
    <div className="bg-[#14161d] border-l-[3px] border-l-[#3954C0] border border-white/10 rounded-2xl p-5 shadow-lg space-y-6">
      {/* Section Header */}
      <div className="flex items-center space-x-2">
        <Send className="w-4 h-4 text-[#3954C0]" />
        <h3 className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98]">
          Staff Review Action
        </h3>
      </div>

      {/* ── 1. Pending Edits Summary ──────────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] flex items-center space-x-2">
          <span>Queued Edits</span>
          <span className="px-1.5 py-0.5 rounded bg-[#1a1d26] text-zinc-300 font-mono border border-white/10 text-[10px]">
            {pendingEdits.length}
          </span>
        </div>

        {pendingEdits.length === 0 ? (
          <p className="text-[13px] text-[#a1a1aa] italic px-1">
            No edits queued. Click the ✎ icon next to any editable field above to make changes.
          </p>
        ) : (
          <div className="space-y-2">
            {pendingEdits.map((edit, idx) => (
              <div
                key={idx}
                className="flex items-start justify-between gap-3 p-3.5 rounded-xl bg-[#1a1d26] border border-white/10"
              >
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center space-x-2 flex-wrap gap-1">
                    <span className="text-[11px] font-mono text-blue-300 bg-[#3954C0]/15 px-2 py-0.5 rounded border border-[#3954C0]/30">
                      {edit.path}
                    </span>
                    <span className="text-[11px] text-[#8b8d98] uppercase tracking-wider">
                      {edit.op}
                    </span>
                  </div>
                  <div className="text-[13px] text-white font-medium truncate">
                    → {String(edit.value)}
                  </div>
                  <div className="text-[12px] text-[#a1a1aa] italic">
                    Reason: {edit.reason}
                  </div>
                </div>
                <button
                  onClick={() => removeEdit(idx)}
                  className="shrink-0 text-[#a1a1aa] hover:text-red-400 transition-colors p-1 rounded"
                  title="Remove edit"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 2. Action Selector ───────────────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98]">
          Select Action
        </div>
        <div className="flex flex-wrap gap-2">
          {actions.map((a) => (
            <button
              key={a.value}
              onClick={() =>
                setSelectedAction((prev) =>
                  prev === a.value ? null : a.value
                )
              }
              className={`flex items-center space-x-2 px-4 py-2 rounded-xl border text-[13px] font-semibold transition-all duration-150 ${
                selectedAction === a.value ? a.activeClass : a.inactiveClass
              }`}
            >
              {a.icon}
              <span>{a.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── 3. Conditional Sub-Form ──────────────────────────────────────────── */}
      {selectedAction === "request_more_information" && (
        <div className="space-y-3 p-4 rounded-xl bg-[#1a1d26] border border-amber-500/20">
          <div className="text-[11px] uppercase tracking-wider font-bold text-amber-400">
            Questions to Send Back
          </div>
          <div className="space-y-2">
            {informationRequestQuestions.map((q, idx) => (
              <div key={idx} className="flex items-start space-x-2">
                <span className="text-[11px] text-[#a1a1aa] font-mono pt-2.5 w-5 text-right shrink-0">
                  {idx + 1}.
                </span>
                <textarea
                  value={q}
                  onChange={(e) => updateQuestion(idx, e.target.value)}
                  placeholder="Enter your question…"
                  rows={2}
                  className="flex-1 bg-[#0a0a0f] border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none focus:border-amber-500/50 resize-none transition-colors"
                />
                {informationRequestQuestions.length > 1 && (
                  <button
                    onClick={() => removeQuestion(idx)}
                    className="text-[#a1a1aa] hover:text-red-400 transition-colors pt-2"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
          {informationRequestQuestions.length < 10 && (
            <button
              onClick={addQuestion}
              className="flex items-center space-x-1.5 text-[13px] text-amber-400 hover:text-amber-300 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Question</span>
            </button>
          )}
        </div>
      )}

      {selectedAction === "approve" && (
        <div className="space-y-3 p-4 rounded-xl bg-[#1a1d26] border border-emerald-500/20">
          <div className="text-[11px] uppercase tracking-wider font-bold text-emerald-400">
            Final Triage Decision
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold">
                Triage Code <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={finalTriage.code}
                onChange={(e) =>
                  setFinalTriage((prev) => ({ ...prev, code: e.target.value }))
                }
                placeholder="e.g. ESI-2, P1, CTAS-1"
                className="w-full bg-[#0a0a0f] border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold">
                Triage Label <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={finalTriage.label}
                onChange={(e) =>
                  setFinalTriage((prev) => ({ ...prev, label: e.target.value }))
                }
                placeholder="e.g. Immediate, Urgent"
                className="w-full bg-[#0a0a0f] border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] text-[#8b8d98] uppercase tracking-wider font-bold">
              Rationale (optional)
            </label>
            <textarea
              value={finalTriage.rationale}
              onChange={(e) =>
                setFinalTriage((prev) => ({
                  ...prev,
                  rationale: e.target.value,
                }))
              }
              placeholder="Clinical rationale for this triage decision…"
              rows={3}
              className="w-full bg-[#0a0a0f] border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none focus:border-emerald-500/50 resize-none transition-colors"
            />
          </div>
        </div>
      )}

      {/* ── 4. Optional Comment ───────────────────────────────────────────────── */}
      <div className="space-y-2">
        <label className="text-[11px] uppercase tracking-wider font-bold text-[#8b8d98]">
          Reviewer Comment (optional)
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Any additional notes for the clinical team…"
          rows={2}
          className="w-full bg-[#1a1d26] border border-white/10 rounded-xl px-3 py-2.5 text-[13px] text-white placeholder-[#5a5d6e] focus:outline-none focus:border-[#3954C0]/50 resize-none transition-colors"
        />
      </div>

      {/* ── 5. Payload Preview (collapsible) ──────────────────────────────────── */}
      {previewPayload && (
        <div className="space-y-2">
          <button
            onClick={() => setPreviewOpen((v) => !v)}
            className="flex items-center space-x-2 text-[11px] uppercase tracking-wider font-bold text-[#8b8d98] hover:text-white transition-colors"
          >
            {previewOpen ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
            <span>Payload Preview</span>
          </button>

          {previewOpen && (
            <pre className="bg-[#0a0a0f] border border-white/10 rounded-xl p-4 text-[11px] font-mono text-zinc-300 overflow-x-auto leading-relaxed custom-scrollbar">
              {JSON.stringify(previewPayload, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* ── 409 Version Conflict Banner ────────────────────────────────────────── */}
      {conflictError && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-300 space-y-3 shadow-md">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="flex-1 text-[13px] leading-relaxed text-amber-200">
              This case was updated elsewhere since you started reviewing (now at version{" "}
              <strong className="text-amber-100 font-bold font-mono">
                v{conflictError.currentServerVersion}
              </strong>
              ). Please review the latest changes before resubmitting.
            </div>
          </div>
          <div className="flex justify-end">
            <button
              onClick={handleRefresh}
              className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-amber-500 text-black text-[12px] font-bold hover:bg-amber-400 transition-colors shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh case</span>
            </button>
          </div>
        </div>
      )}

      {/* ── 6. Submit Button + Toast ──────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 pt-1 border-t border-white/8">
        {/* Bug 2: show helper text when approve is blocked by required gaps */}
        {selectedAction === "approve" && unresolvedRequiredGaps.length > 0 && (
          <p className="text-[12px] text-amber-400 font-semibold flex items-center space-x-1.5">
            <span>⚠</span>
            <span>
              Resolve {unresolvedRequiredGaps.length} required information gap
              {unresolvedRequiredGaps.length > 1 ? "s" : ""} first (scroll up to
              Information Gaps).
            </span>
          </p>
        )}

        <div className="flex items-center justify-between gap-4">
          {submitted ? (
            <div className="flex items-center space-x-2 text-emerald-400 text-[13px] font-semibold">
              <CheckCircle2 className="w-5 h-5" />
              <span>Review submitted (mock) — payload logged to console.</span>
            </div>
          ) : (
            <p className="text-[12px] text-[#5a5d6e] italic">
              No real network call is made in this prototype.
            </p>
          )}

          <button
            onClick={handleSubmit}
            disabled={!canSubmit()}
            className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl text-[13px] font-bold transition-all duration-150 ${
              canSubmit()
                ? "bg-[#3954C0] text-white hover:bg-[#4a65d0] shadow-lg shadow-[#3954C0]/25 hover:shadow-[#3954C0]/40"
                : "bg-[#1a1d26] text-[#5a5d6e] cursor-not-allowed border border-white/10"
            }`}
          >
            <Send className="w-4 h-4" />
            <span>Submit Review</span>
          </button>
        </div>
      </div>
    </div>
  );
}
