import { StaffReviewPayload } from "@/types/staffReview";
import { StructuredCase } from "@/types/structuredCase";

export const ROLE3_BASE = process.env.NEXT_PUBLIC_ARIA_API_URL ?? "/role3";
export const STAFF_TOKEN =
  process.env.NEXT_PUBLIC_ARIA_STAFF_TOKEN ?? "staff-demo-token";

export type CaseEventType =
  | "case.snapshot"
  | "case.updated"
  | "case.tool_status"
  | "case.review_status"
  | "case.error";

export interface CaseEvent {
  eventId: string;
  eventType: CaseEventType;
  caseId: string;
  caseVersion: number;
  occurredAt: string;
  data: {
    structuredCase?: StructuredCase | null;
    reviewStatus?: string;
    action?: string;
    reviewerId?: string;
    tool?: string;
    status?: string;
    result?: unknown;
    [key: string]: unknown;
  };
}

export interface CaseSnapshot {
  caseId: string;
  sessionId: string | null;
  caseVersion: number;
  reviewStatus: string;
  structuredCase: StructuredCase | null;
  linkedPatientPublicId: string | null;
}

export interface ReviewAccepted {
  status: string;
  caseId: string;
  reviewerId?: string;
  baseCaseVersion?: number;
  caseVersion?: number;
  questions?: string[];
  approvedRecord?: {
    status?: string;
    approvedRecordPublicId?: string;
  };
}

export class Role3Error extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public latestCaseVersion?: number,
    public fieldErrors: { path: string; message: string }[] = []
  ) {
    super(message);
    this.name = "Role3Error";
  }
}

function authHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  headers.set("Authorization", `Bearer ${STAFF_TOKEN}`);
  return headers;
}

async function parseError(response: Response): Promise<Role3Error> {
  let code = "HTTP_ERROR";
  let message = "Request failed.";
  let latestCaseVersion: number | undefined;
  let fieldErrors: { path: string; message: string }[] = [];
  try {
    const body = await response.json();
    const err = body?.error ?? {};
    code = err.code ?? code;
    message = err.message ?? message;
    latestCaseVersion =
      typeof err.latestCaseVersion === "number" ? err.latestCaseVersion : undefined;
    fieldErrors = Array.isArray(err.fieldErrors) ? err.fieldErrors : [];
  } catch {
    /* content-safe fallback */
  }
  return new Role3Error(response.status, code, message, latestCaseVersion, fieldErrors);
}

async function role3Fetch(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${ROLE3_BASE}${path}`, {
      ...init,
      headers: authHeaders(init?.headers),
    });
  } catch {
    throw new Role3Error(0, "BACKEND_UNAVAILABLE", "Role 3 is not reachable.");
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  return response;
}

export async function getHealth(): Promise<{ status: string; role: string }> {
  let response: Response;
  try {
    response = await fetch(`${ROLE3_BASE}/health`);
  } catch {
    throw new Role3Error(0, "BACKEND_UNAVAILABLE", "Role 3 is not reachable.");
  }
  if (!response.ok) {
    throw new Role3Error(response.status, "BACKEND_UNAVAILABLE", "Role 3 is not reachable.");
  }
  return response.json();
}

export async function getCaseSnapshot(caseId: string): Promise<CaseSnapshot> {
  const response = await role3Fetch(`/api/v1/cases/${encodeURIComponent(caseId)}`);
  return response.json();
}

export async function lookupPatientAuthorised(opts: {
  phone?: string;
  patientPublicId?: string;
}): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (opts.phone) params.set("phone", opts.phone);
  if (opts.patientPublicId) params.set("patientPublicId", opts.patientPublicId);
  const response = await role3Fetch(`/api/v1/patients/lookup?${params.toString()}`);
  return response.json();
}

export async function submitStaffReview(
  payload: StaffReviewPayload
): Promise<ReviewAccepted> {
  const response = await role3Fetch(
    `/api/v1/cases/${encodeURIComponent(payload.caseId)}/reviews`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": payload.idempotencyKey,
      },
      body: JSON.stringify(payload),
    }
  );
  return response.json();
}

function parseSseBlock(block: string): CaseEvent | null {
  let eventId = "";
  let eventType = "";
  let dataRaw = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("id:")) eventId = line.slice(3).trim();
    else if (line.startsWith("event:")) eventType = line.slice(6).trim();
    else if (line.startsWith("data:")) dataRaw += line.slice(5).trim();
  }
  if (!dataRaw) return null;
  try {
    const envelope = JSON.parse(dataRaw) as CaseEvent;
    if (eventId) envelope.eventId = envelope.eventId || eventId;
    if (eventType) envelope.eventType = (envelope.eventType || eventType) as CaseEventType;
    return envelope;
  } catch {
    return null;
  }
}

export function subscribeCaseEvents(
  caseId: string,
  onEvent: (event: CaseEvent) => void,
  onError?: (error: Role3Error) => void
): () => void {
  const abort = new AbortController();
  let lastEventId: string | undefined;
  let stopped = false;

  const connect = async () => {
    while (!stopped) {
      try {
        const headers = authHeaders({ Accept: "text/event-stream" });
        if (lastEventId) headers.set("Last-Event-ID", lastEventId);
        const response = await fetch(
          `${ROLE3_BASE}/api/v1/cases/${encodeURIComponent(caseId)}/events`,
          { headers, signal: abort.signal }
        );
        if (!response.ok) {
          throw await parseError(response);
        }
        if (!response.body) {
          throw new Role3Error(502, "SSE_UNAVAILABLE", "Role 3 did not return an event stream.");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!stopped) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";
          for (const part of parts) {
            const event = parseSseBlock(part.trim());
            if (!event) continue;
            lastEventId = event.eventId;
            onEvent(event);
          }
        }
      } catch (error) {
        if (stopped || abort.signal.aborted) return;
        if (error instanceof Role3Error && (error.status === 401 || error.status === 403)) {
          onError?.(error);
          return;
        }
        onError?.(
          error instanceof Role3Error
            ? error
            : new Role3Error(0, "SSE_RECONNECTING", "Reconnecting to Role 3.")
        );
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
    }
  };

  void connect();
  return () => {
    stopped = true;
    abort.abort();
  };
}
