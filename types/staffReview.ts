export interface PendingEdit {
  op: "add" | "replace" | "remove";
  path: string; // JSON Pointer e.g. "/chiefComplaint/text"
  value: unknown;
  reason: string;
}

export type ReviewAction =
  | "save_draft"
  | "request_more_information"
  | "approve"
  | null;

export interface FinalTriage {
  code: string;
  label: string;
  rationale: string;
}

export interface StaffReviewPayload {
  schemaVersion: "1.0.0";
  caseId: string;
  baseCaseVersion: number;
  idempotencyKey: string;
  action: "save_draft" | "request_more_information" | "approve";
  edits: PendingEdit[];
  informationRequest: { questions: string[] } | null;
  finalTriage: FinalTriage | null;
  comment: string | null;
}
