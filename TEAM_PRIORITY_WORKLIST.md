# AI Emergency Intake - Priority Worklist

Status basis: architecture draft v3 dated 1 September 2026. This is a proposed execution plan; each owner must confirm current implementation readiness. Existing schemas and example payloads are draft integration assets, not proof that the implementation is complete.

## Confirmed team ownership

- Role 1 - Voice AI: Shahzaib Fraz
- Role 2 - AI / Agent: Fazwan Zainuddin
- Role 3 - Backend: Mozzam Shahid
- Role 4 - Database & Integration: Ishaan Sama
- Role 5 - Frontend: Jonathan
- Demo and presentation: Mariam Habib

Role ownership is fixed. Each owner still needs to report implementation readiness, next evidence, blockers and target test date.

## Priority 0 - Freeze the shared contracts

This is the first team action and should be completed before final integration.

1. Roles 2, 3 and 5 agree:
   - structured-case field names;
   - SSE event names and event envelope;
   - full snapshot versus partial updates;
   - case and event version handling;
   - unknown values, sources and confidence handling;
   - protection of staff corrections from later AI updates.
2. Roles 3, 4 and 5 agree:
   - database choice and identifier mapping;
   - authentication and permissions;
   - reconnect and event replay behaviour;
   - review submission, approved save and error responses.
3. The domain/clinical owner confirms:
   - final-triage code system;
   - authorised approver roles;
   - mandatory fields for approval.

Output: one agreed contract version, one example `StructuredCase`, one example staff review, and named owners for every open decision.

## Priority 1 - Parallel owner work

| Owner | Start now | Handoff | Depends on | Blocks | Evidence of completion |
|---|---|---|---|---|---|
| Role 1 - Voice / Shahzaib Fraz | Produce transcript turns, session ID/status, turn detection and interruption handling using synthetic audio. Connect spoken follow-up questions and answers. | Final transcript and session references to Role 2; spoken-response completion to the agreed consumer. | Role 2 supplies approved follow-up response text/prompt configuration for the final connection. | Role 2 cannot test the real conversation loop without transcript turns. | One synthetic spoken exchange becomes text, then one follow-up question and answer completes. |
| Role 2 - AI / Fazwan Zainuddin | Finalise extraction fields, safety-signal vocabulary, source mapping and prompt outputs. Prepare sufficient, missing-information and conflicting-information examples. | Response text to Role 1; tool request and `StructuredCase` payload to Role 3. | Can begin with synthetic examples; final output depends on Priority 0 and Role 1 transcript format. | Role 3 ingestion and Role 5 field display cannot be finalised without the agreed structured payload. | All three examples validate against the frozen schema and are ready for Role 3. |
| Role 3 - Backend / Mozzam Shahid | Build FastAPI intake/review interfaces, schema validation, authentication, standard errors, idempotency and case-version checks. Publish snapshot/update/tool-status/review-status events through SSE with reconnection support. | Queries and approved saves to Role 4; SSE events to Role 5; actual tool results to Role 2; confirmed response to Role 1. | Contract decisions from Roles 2/5; persistence mapping from Role 4; review fields from Role 5. | Central integration bottleneck: live dashboard, retrieval, review and save all pass through Role 3. | One accepted structured case reaches Role 5; reconnect works; stale update returns 409; review/save confirmation returns. |
| Role 4 - Data / Ishaan Sama | Confirm database, case/patient identifiers, synthetic records, authorised retrieval, approved-record schema, audit log, retention and privacy rules. | Verified record/not-found/conflict/save result to Role 3. | Priority 0 identifier and save contract; domain retention/privacy decisions. | Context retrieval and final approved save cannot complete without this layer. | One synthetic lookup, one not-found result, and one approved record saved once with an audit trail. |
| Role 5 - Frontend / Jonathan | Build through an adapter using example payloads. Display draft, source/confidence, gaps, conflicts and tool status. Preserve staff edits and submit draft/request-more-information/approve actions. | Staff corrections, action request and approval to Role 3. | Can build mock UI now; live behaviour depends on Role 3 SSE and review API. | Human-review demo cannot complete until staff actions and save status are visible. | One live update appears without refresh; staff corrections survive later updates; save/conflict status is visible. |
| Demo - Mariam Habib | Draft the synthetic demo script and expected checkpoints now; schedule the joint run after owners report readiness. Clearly label simulated components. | Demo scenario, test order, notes and presentation flow to the whole team. | Requires the minimum vertical slice from Roles 1-5 for the final rehearsal. | Final competition demonstration and presentation readiness. | One complete intake-to-review-to-save run with no real patient data. |

## Ishaan Sama contribution incorporated

The team plan now explicitly considers Ishaan Sama's EmergencyVoice tech-stack proposal:

- AssemblyAI Voice Agent signals: STT, VAD/turn-taking, sentiment, disfluency, word timestamps and tool calling.
- Browser/WebRTC as the fastest demo transport; Twilio remains an optional upgrade.
- JSON-Schema tool calling with nullable/unknown fields and no forced clinical values.
- An auditable distress indicator derived from sentiment, disfluency and pacing, kept separate from clinical severity and final triage.
- Synthetic mock records, server-side filtered lookup, audit and retention; SQLite is sufficient for MVP while Postgres remains an option.
- A fixed structured brief delivered through the current FastAPI + SSE path with visible human review.
- PII redaction, explicit deletion/retention rules and no autonomous diagnosis or triage scoring.

Open choices remain: exact AssemblyAI model/API availability, browser-only vs Twilio, SQLite vs Postgres, LeMUR vs the current LLM path, distress formula and transcript/audio retention.

## Priority 2 - Integration order

1. Role 1 sends a final synthetic transcript to Role 2.
2. Role 2 sends the agreed `StructuredCase` to Role 3.
3. Role 3 validates it and publishes an SSE snapshot/update to Role 5.
4. Role 5 displays the draft, gaps, conflicts, sources and confidence.
5. Role 3 requests verified context from Role 4 and returns the result to Role 2.
6. Role 2 reconciles the new information and sends a new case version.
7. Role 5 submits staff edits or approval to Role 3.
8. Role 3 sends the approved save to Role 4.
9. Role 4 stores the approved record and audit trail exactly once.
10. Role 3 sends the final review/save status to Role 5.

## Critical path and bottlenecks

```text
Contract freeze
  -> Role 2 structured payload
  -> Role 3 validation + SSE
  -> Role 5 live review
  -> Role 3 review API
  -> Role 4 approved save
  -> End-to-end demo
```

- Main technical bottleneck: Role 3, because it owns validation, authentication, routing, SSE, review submission and save orchestration.
- Main decision bottleneck: the Priority 0 contract and database/auth decisions.
- Safety decision bottleneck: no final approval flow can be considered complete until the domain/clinical owner confirms triage codes, approvers and mandatory fields.
- Data-integrity bottleneck: version checks, idempotency, SSE replay and protection of staff edits must work before the demo is called complete.

No owner needs to wait completely. Roles 1, 2, 4 and 5 can build against synthetic examples in parallel while Role 3 scaffolds the backend, but the final integration must use the frozen contract.

## First checkpoint

The first shared target is:

> One synthetic case reaches the dashboard through SSE, is reviewed by staff, and is saved once with an audit trail.

Each owner should reply with:

1. Agree or requested contract change.
2. What is ready now.
3. Next deliverable.
4. Current blocker and the person/role needed to unblock it.
5. Target date for the first integration test.

## Copy-paste Discord message

Team, here is the proposed priority and dependency order based on our workflow document. Please treat implementation status as unconfirmed until each owner replies.

**P0 - Contract gate:** Roles 2/3/5 agree the payload fields, SSE events, snapshot vs partial updates, versions, source/unknown handling and staff-edit protection. Roles 3/4/5 agree the database, authentication, reconnect and review/save behaviour. We also need the domain/clinical owner to confirm triage codes, authorised approvers and mandatory approval fields.

**P1 - Work in parallel:**

1. **Role 1 - Voice:** deliver transcript turns and session references; prove one synthetic spoken exchange plus one follow-up question/answer. Handoff to Role 2.
2. **Role 2 - AI/Agent:** finalise extraction fields, sources, confidence, safety signals and prompts; deliver sufficient, missing and conflicting examples as an agreed `StructuredCase`. Handoff to Role 3.
3. **Role 3 - Backend:** build validation/auth/version/idempotency, SSE publishing/reconnect and staff-review APIs. Handoff SSE to Role 5 and data/save requests to Role 4. This is the main integration bottleneck.
4. **Role 4 - Data:** confirm DB/IDs, synthetic retrieval, approved-record storage and audit trail; return verified/not-found/save results to Role 3.
5. **Role 5 - Frontend:** build against the examples now; display draft/gaps/conflicts/source/confidence, preserve staff edits and send review/approval to Role 3.
6. **Mariam Habib - Demo:** prepare the synthetic script now and coordinate the full rehearsal once the minimum flow is ready.

**Critical path:** contract freeze -> Role 2 payload -> Role 3 validation/SSE -> Role 5 review -> Role 3 review API -> Role 4 save -> demo.

**First target:** one synthetic case reaches the dashboard through SSE, is reviewed by staff and is saved once with an audit trail.

Please reply with: (1) agree/change, (2) what is ready, (3) next deliverable, (4) blocker and who you need, and (5) target test date.
