import type { PendingEdit, StaffReviewPayload } from "../types/staffReview";
import type { ConflictItem, InformationGap, StructuredCase } from "../types/structuredCase";

export type EventDecision = "duplicate" | "stale" | "apply";

export function shouldApplyEvent(
  eventId: string,
  eventVersion: number,
  seenIds: ReadonlySet<string>,
  currentVersion: number
): EventDecision {
  if (seenIds.has(eventId)) return "duplicate";
  if (eventVersion < currentVersion) return "stale";
  return "apply";
}

export function unresolvedRequiredGaps(
  gaps: InformationGap[] | undefined,
  pendingEdits: PendingEdit[]
): InformationGap[] {
  return (gaps ?? []).filter(
    (gap) =>
      gap.priority === "required" && !pendingEdits.some((edit) => edit.path === gap.fieldPath)
  );
}

export function canApproveReview(input: {
  triageCode: string;
  triageLabel: string;
  unresolvedRequiredCount: number;
  reviewStatus?: string;
}): boolean {
  if (input.reviewStatus === "approved") return false;
  if (!input.triageCode.trim() || !input.triageLabel.trim()) return false;
  if (input.unresolvedRequiredCount > 0) return false;
  return true;
}

export function parseConflictVersion(errorBody: unknown): number | undefined {
  if (!errorBody || typeof errorBody !== "object") return undefined;
  const err = (errorBody as { error?: { latestCaseVersion?: unknown } }).error;
  return typeof err?.latestCaseVersion === "number" ? err.latestCaseVersion : undefined;
}

export function conflictToEdit(
  caseItem: StructuredCase,
  conflict: ConflictItem,
  valueIndex: number
): PendingEdit | null {
  const chosen = conflict.values[valueIndex];
  if (!chosen) return null;

  if (conflict.fieldPath.startsWith("/safetySignals/")) {
    const code = conflict.fieldPath.slice("/safetySignals/".length);
    const index = caseItem.safetySignals.findIndex((signal) => signal.code === code);
    if (index < 0) return null;
    return {
      op: "replace",
      path: `/safetySignals/${index}/status`,
      value: "staff_reviewed",
      reason: `Staff resolved conflicting safety signal using: ${chosen.value}`,
    };
  }

  if (conflict.fieldPath === "/history/allergies") {
    return {
      op: "replace",
      path: "/history/allergies",
      value: [
        {
          name: chosen.value,
          status: "reported",
          details: "Resolved by staff during review",
          sourceRefs: [...chosen.sourceRefs, "staff_review"],
        },
      ],
      reason: `Staff resolved allergy conflict: ${chosen.value}`,
    };
  }

  return {
    op: "replace",
    path: conflict.fieldPath,
    value: chosen.value,
    reason: `Staff selected verified value during review: ${chosen.value}`,
  };
}

export function buildStaffReviewPayload(input: {
  caseId: string;
  caseVersion: number;
  action: StaffReviewPayload["action"];
  edits: PendingEdit[];
  questions?: string[];
  triageCode?: string;
  triageLabel?: string;
  rationale?: string | null;
  comment?: string | null;
  idempotencyKey: string;
}): StaffReviewPayload {
  return {
    schemaVersion: "1.0.0",
    caseId: input.caseId,
    baseCaseVersion: input.caseVersion,
    idempotencyKey: input.idempotencyKey,
    action: input.action,
    edits: input.edits,
    informationRequest:
      input.action === "request_more_information"
        ? { questions: (input.questions ?? []).filter((question) => question.trim()) }
        : null,
    finalTriage:
      input.action === "approve"
        ? {
            code: (input.triageCode ?? "").trim(),
            label: (input.triageLabel ?? "").trim(),
            rationale: (input.rationale ?? "").trim() || null,
          }
        : null,
    comment: (input.comment ?? "").trim() || null,
  };
}
