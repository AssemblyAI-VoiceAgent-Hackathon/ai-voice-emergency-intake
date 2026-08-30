# Role 2 - Role 3 - Role 5 Integration Contract (Draft v1)

Status: proposed contract for team confirmation.  
Owners: Role 2 owns extraction semantics; Role 3 owns API, authentication, validation and event delivery; Role 5 owns UI state, staff review and submission.

## 1. What Role 2 delivers

Role 2 sends a `StructuredCase` that follows `structured-case.schema.json`.

The object contains:

- Case/session identifiers and a monotonically increasing version.
- Chief complaint, symptoms, reported or measured observations and relevant history.
- A concise summary.
- Missing-information questions and conflicting statements.
- Field-level source, confidence and verification metadata.
- Safety signals for staff attention.

It deliberately does **not** contain a diagnosis or final triage decision. Final triage remains a human decision.

## 2. Proposed Role 2 to Role 3 ingestion

Role 3 owns the final route name. Proposed MVP route:

```http
POST /api/v1/cases/{caseId}/structured-case
Content-Type: application/json
Authorization: Bearer <service-token>
Idempotency-Key: <caseId>-<caseVersion>
```

Body: `structured-case.schema.json`.

Recommended responses:

- `202 Accepted`: validated and queued/published.
- `400 Bad Request`: malformed JSON.
- `401/403`: authentication or permission failure.
- `409 Conflict`: stale `caseVersion` or duplicate incompatible update.
- `422 Unprocessable Entity`: schema-valid JSON with invalid business state.

Every error should use one envelope:

```json
{
  "error": {
    "code": "CASE_VERSION_CONFLICT",
    "message": "The submitted case version is stale.",
    "fieldErrors": [
      { "path": "/caseVersion", "message": "Expected version 4." }
    ],
    "requestId": "req_demo_001"
  }
}
```

## 3. Proposed Role 3 to Role 5 live stream

For the MVP, use SSE because the live flow is mainly Role 3 publishing updates to Role 5. Staff commands travel in the opposite direction through authenticated REST calls.

Proposed route:

```http
GET /api/v1/cases/{caseId}/events
Accept: text/event-stream
Authorization: Bearer <staff-token>
```

Proposed event envelope:

```json
{
  "eventId": "evt_demo_004",
  "eventType": "case.updated",
  "caseId": "case_demo_001",
  "caseVersion": 4,
  "occurredAt": "2026-08-30T09:16:00Z",
  "data": {}
}
```

Initial event names:

- `case.snapshot`: complete state after connection/reconnection.
- `case.updated`: validated structured-case update.
- `case.tool_status`: backend/tool progress for the dashboard.
- `case.review_status`: draft saved, more information requested or approval completed.
- `case.error`: recoverable case-specific error that the UI should display.

Role 3 should support SSE `id` values and reconnection through `Last-Event-ID`. Role 5 must ignore duplicate `eventId` values and must not apply an event with an older `caseVersion`.

## 4. Proposed Role 5 to Role 3 review submission

Proposed route:

```http
POST /api/v1/cases/{caseId}/reviews
Content-Type: application/json
Authorization: Bearer <staff-token>
Idempotency-Key: <unique-review-key>
```

Body: `staff-review.schema.json`.

Important rules:

- Role 3 obtains reviewer identity and permissions from authentication; it does not trust a reviewer ID supplied by the browser.
- `baseCaseVersion` is required for optimistic concurrency.
- A `409 Conflict` returns the latest case version so Role 5 can prompt the staff member to review changes.
- Role 3 validates every edit path and records the old value, new value, reviewer, timestamp and reason in the audit log.
- `finalTriage` is mandatory only when `action` is `approve`, and its permitted code system must be confirmed by the clinical/domain owner.
- Role 3 sends the approved save to Role 4; Role 5 never writes directly to the database.

## 5. Security and privacy minimums

- Use synthetic data during development and demos unless the team has approved a protected-data environment.
- Do not write transcripts, authorization tokens or patient details to ordinary application logs.
- Enforce least-privilege access and server-side authorization for every case.
- Encrypt traffic, set retention rules and keep an immutable audit trail for staff edits/approval.
- Display source and verification state so reported information is not mistaken for a verified clinical fact.

## 6. Decisions the team must confirm

Role 2:

- Confirm the required intake fields, safety-signal vocabulary and extraction prompt output.
- Confirm how source references map to transcript turns, staff observations and verified records.

Role 3:

- Confirm route names, SSE versus WebSocket, authentication, event replay/retention and error envelope.
- Implement schema validation, version conflicts, idempotency and audit logging.

Role 4:

- Confirm patient/case identifiers, persistence mapping, approved-record schema and retention/privacy rules.

Role 5:

- Confirm which fields are editable, how missing/conflicting/low-confidence information appears and the conflict-resolution UX.
- Build against the example payloads through an adapter so API route changes do not require UI rewrites.

Domain/clinical owner:

- Confirm the triage code system, authorized approver roles and mandatory fields before approval.

## 7. Integration definition of done

- Both JSON examples validate against their schemas.
- Role 2 can submit a synthetic structured case and receive an accepted response.
- Role 5 receives a snapshot, one update and a tool-status event, including after reconnection.
- Role 5 can save a draft, request more information and approve a case.
- A stale edit produces a clear `409` flow without data loss.
- Unauthorized access is rejected and sensitive content is absent from normal logs.
- Role 4 stores the approved record and audit trail once, without duplicate writes.
- The team demonstrates one complete synthetic case from intake through human approval.

## 8. Copy-paste team message

> I have prepared Draft v1 of the Role 2 structured-case contract, a synthetic example and the proposed Role 5 staff-review payload. Role 3, please confirm the route names, authentication, version-conflict response and whether we will use SSE for the MVP. Role 4, please confirm the identifier and persistence mapping. Role 5 can proceed now against the example payloads through an adapter. The AI output contains sources, confidence, missing information, conflicts and safety signals, but no diagnosis or final triage decision; final triage remains staff-owned. Please comment on the open decisions before implementation is frozen.
