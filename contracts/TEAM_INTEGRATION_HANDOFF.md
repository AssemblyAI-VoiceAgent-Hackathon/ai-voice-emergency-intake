# Team Integration and Handoff Contract (v4)

**Status:** Current team coordination baseline, dated 3 September 2026.
**Scope:** Defines ownership, delivery locations, and handoffs for Roles 1–5. It does not by itself prove that an implementation is complete.

## 1. Single source of truth

- The active product repository is `AssemblyAI-VoiceAgent-Hackathon/ai-voice-emergency-intake`.
- The `main` branch contains only work that has been reviewed and merged.
- Feature branches are temporary workspaces. A file on a feature branch is not part of `main` until its pull request is merged.
- The ARIA GitHub Project board is the source of truth for task status.
- The separate organisation repositories named `backend` and `frontend` are not delivery locations for this project unless the team explicitly approves a migration.

## 2. Ownership and delivery locations

| Role | Owner | Owns and delivers | Canonical path |
|---|---|---|---|
| Role 1 — Voice AI | Soha Raees (`@soharaees`) | AssemblyAI connection, microphone/audio streaming, STT/TTS, turn detection, interruption handling, and final transcript events | `src/voice/` |
| Role 2 — AI / Agent | Fazwan Zainuddin | Prompting, extraction logic, schema-conformant structured cases, confidence and safety guardrails | `src/extraction/` |
| Role 3 — Backend | Mozzam Shahid | API endpoints, authentication, validation, tool execution, orchestration, retries, notifications and event publishing | `backend/` |
| Role 4 — Database & Integration | Ishaan Sama | Patient data model, persistence, authorised retrieval, audit, retention and database integrations | `src/data/` |
| Role 5 — Frontend | Jonathan | Live dashboard, intake display, confidence/source display, staff review, correction and final submission | `src/dashboard/` |
| Demo & presentation | Mariam Habib | Demo flow, evidence capture and presentation material | `demo/`, `presentation/` |

Owners may add subfolders under their canonical path. They should not create a new repository or a second top-level implementation path without team agreement.

## 3. End-to-end handoff

1. **Role 1 → Role 2:** Role 1 emits final, non-agent transcript turns that conform to `contracts/intake-transcript.schema.json`. Each turn carries a stable `turnId`, session identifier, timestamp, speaker and finality state.
2. **Role 2 → Role 3:** Role 2 converts accepted transcript evidence into a `StructuredCase` conforming to `contracts/structured-case.schema.json`, with stable source references and validation errors when input is incomplete or invalid.
3. **Role 3 ↔ Role 4:** Role 3 sends authenticated, validated data requests. Role 4 returns authorised records, not-found responses, conflicts and save confirmations. Role 4 owns storage rules; Role 3 owns API and workflow behaviour.
4. **Role 3 → Role 5:** Role 3 publishes live case events, tool status and validated structured data. Role 5 renders those events and never writes directly to the database.
5. **Role 5 → Role 3:** Role 5 submits staff corrections, approval and final triage selection through backend endpoints. Role 3 validates and executes them.
6. **Role 3 → Role 2 → Role 1:** Confirmed tool results may update the agent context. Role 2 decides response content; Role 1 handles spoken delivery and the live voice interaction.

## 4. Role 1 deliverable and handoff details

Role 1 was missing from the earlier Role 2/3/5 document. The required Role 1 delivery is now explicit:

- Put implementation code under `src/voice/`.
- Document local setup, environment-variable names and the command used to run the voice service in `src/voice/README.md`.
- Emit transcript payloads matching `contracts/intake-transcript.schema.json`.
- Use final transcript turns for downstream extraction; interim transcript text is for live display only.
- Preserve `sessionId` and stable `turnId` values so Role 2 can cite the original evidence.
- Handle connection failure, microphone failure, reconnect, interruption and end-of-session behaviour.
- Add automated tests under `tests/voice/` or the repository's agreed test layout.
- Open a pull request linked to the assigned GitHub issue and include test evidence.

Role 1 must not implement extraction policy, backend business logic, database persistence or dashboard UI.

## 5. Shared contracts

- `contracts/intake-transcript.schema.json`: Role 1 output and Role 2 input.
- `contracts/structured-case.schema.json`: Role 2 output and Role 3/5 input.
- `contracts/staff-review.schema.json`: Role 5 action and Role 3 input.
- `contracts/examples/`: representative payloads used for integration checks.

Any contract change must be made in a pull request and reviewed by every directly affected role before merge. Do not hard-code a competing field name in an implementation branch.

## 6. Status and evidence rules

Every owner must keep the assigned ARIA item current:

1. Move `Backlog` to `In Progress` when implementation starts.
2. Add a comment stating the branch, current deliverable, blocker (if any), and expected test date.
3. Move to `In Review` when a pull request is open and link the pull request.
4. Move to `Done` only after the work is merged to `main` and evidence is recorded.

Chat messages and work visible only on a local machine are not completion evidence. Valid evidence is a linked commit, pull request, test result, screenshot, or demo recording in the GitHub issue.

## 7. Definition of done for a role delivery

A role delivery is complete only when:

- the implementation is in its canonical path;
- its interface matches the shared schemas;
- setup and test instructions are documented;
- relevant tests pass;
- a pull request has been reviewed and merged to `main`; and
- the linked ARIA item is updated to `Done` with evidence.

Until these conditions are met, the work remains `Backlog`, `In Progress`, or `In Review` even if someone reports in chat that it is finished.
