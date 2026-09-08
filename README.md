# AI Voice Emergency Intake

Private team repository for an AI-assisted voice intake prototype. The system is intended to capture spoken emergency-intake information, convert it into a structured case, pass it through a secure backend, and present it to authorised staff for human review.

> This prototype does not diagnose patients or make the final triage decision. A qualified human reviewer remains responsible for verification, triage and approval.

**New to this repo?** See [GETTING_STARTED.md](GETTING_STARTED.md) for a full step-by-step guide: what to install, how to configure `.env`, and how to run and try the whole system locally.

## Confirmed team roles

| Role | Team member | GitHub |
|---|---|---|
| Role 1 — Voice / conversation | Soha Raees | [@soharaees](https://github.com/soharaees) |
| Role 2 — AI extraction | Fazwan Zainuddin | [@fazwanproperty](https://github.com/fazwanproperty) |
| Role 3 — Backend / integration | Mozzam Shahid | [@MozzamShahid](https://github.com/MozzamShahid) |
| Role 4 — Data / persistence | Ishaan Sama | [@IshaanSama038X](https://github.com/IshaanSama038X) |
| Role 5 — Staff dashboard / review | Jonathan | [@halojonathan](https://github.com/halojonathan) |
| Demo and presentation | Mariam Habib | [@MaryamHabib2](https://github.com/MaryamHabib2) |

## Current repository contents

- `contracts/structured-case.schema.json` — Role 2 structured extraction contract.
- `contracts/intake-transcript.schema.json` — Role 1/3 source envelope accepted by Role 2.
- `contracts/staff-review.schema.json` — Role 5 staff-review contract.
- `contracts/examples/` — synthetic sufficient, missing and conflicting payloads.
- `contracts/TEAM_INTEGRATION_HANDOFF.md` — complete Role 1–5 ownership, delivery paths and integration workflow.
- `src/voice/` — Role 1 AssemblyAI voice capture. Emits `intake-transcript` turns, runs Role 2 extraction, and ingests into Role 3.
- `src/extraction/` — provider-neutral, schema-first extraction and safe-failure engine.
- `src/backend/` — Role 3 FastAPI ingestion, SSE, staff review, tool calling, and Role 4 save handoff.
- `src/data/` — Role 4 persistence (Supabase hosted, SQLite for tests), authorised lookup, approved-record save, audit trail, and synthetic fixtures.
- `app/`, `components/dashboard/` — Role 5 staff review UI (Next.js). Talks only to Role 3; never writes to the database.
- `supabase/migrations/` — Postgres schema for the hosted Supabase project.
- `TEAM_PRIORITY_WORKLIST.md` — owner priorities, dependencies, integration order and first shared checkpoint.
- `output/pdf/AI_Emergency_Intake_Team_Workflow_Roles.pdf` — current team workflow (v4), confirmed role reference and Ishaan Sama contribution map.
- `output/pdf/AI_Emergency_Intake_Team_Workflow_Roles_v5.pdf` — exact versioned mirror of the current team workflow.
- `output/pdf/AI_Emergency_Intake_Team_Workflow_Roles_v4.pdf` — preserved previous version.
- `output/pdf/Role3_Role4_Simple_Flowchart.pdf` — plain-English Role 3 / Role 4 flowchart for non-technical teammates (companion to v4, not a replacement).

The workflow PDF is the confirmed role reference: Soha Raees (Role 1), Fazwan Zainuddin (Role 2), Mozzam Shahid (Role 3), Ishaan Sama (Role 4), Jonathan (Role 5), and Mariam Habib (demo and presentation). It also maps Ishaan Sama's EmergencyVoice tech-stack contribution into the shared FastAPI + SSE plan.

## Repository and delivery map

This repository is the single active product repository. The organisation repositories named `backend` and `frontend` are currently empty and are not part of this delivery workflow. Do not push project work to them unless the team first approves and documents a migration.

| Owner | Delivery path in this repository |
|---|---|
| Role 1 — Soha | `src/voice/` |
| Role 2 — Fazwan | `src/extraction/` |
| Role 3 — Mozzam | `src/backend/` |
| Role 4 — Ishaan | `src/data/` |
| Role 5 — Jonathan | `app/dashboard/`, `components/dashboard/`, `lib/` and `types/` |
| Demo — Mariam | `demo/` and `presentation/` |

A branch is a temporary version of this same repository, not a separate delivery folder. GitHub shows a branch's own snapshot: an older branch can still show an old PDF or return a 404 for a file that was added later on `main`. Only reviewed and merged work appears on `main`.

## Verified implementation snapshot — 8 September 2026

| Area | Evidence currently visible in GitHub | Interpretation |
|---|---|---|
| Shared contracts and workflow | Present on `main` | Available to all roles as the integration baseline. |
| Role 1 — Voice | `src/voice/` is present on `main`, built by Soha Raees; Issues #1, #13 and #14 are closed; the demo handoff is covered by tests and a local smoke test | Role 1 is delivered. Live AssemblyAI operation still requires a securely configured key. |
| Role 2 — Extraction | `src/extraction/`, the OpenAI-compatible adapter, demo fallback, contract examples and tests are present on `main`; Issues #2, #15 and #16 are closed | Role 2 is delivered. A real LLM requires OpenRouter or OpenAI configuration. |
| Role 3 — Backend | `src/backend/` and backend tests are present on `main`; Issues #3, #17 and #19 are closed | Role 3 is delivered on `main`. |
| Role 4 — Data | `src/data/`, the Supabase migration, synthetic fixtures and tests are present on `main`; Issues #4, #20 and #21 are closed | Role 4 is delivered on `main`. |
| Role 5 — Dashboard | `app/dashboard/`, dashboard components and workflow tests are present on `main`; Issues #5, #22 and #23 are closed | Role 5 is delivered on `main`. |

All five role implementations are now present on `main`. Component completion is not the same as competition readiness: the remaining delivery gates are the cross-role synthetic end-to-end demonstration (#7), domain/safety review (#6), and competition demo/presentation preparation (#11). PR #35 must not be merged while it contains a committed `.env`; exposed keys must be rotated and the credit-only documentation change resubmitted without secrets. The current production dependency audit also reports two high-severity findings through Next.js 14.2.35; upgrade or document mitigations before an internet-facing deployment. Team members must keep ARIA status aligned and attach repository or test evidence.

## Proposed architecture

1. Voice intake captures the conversation.
2. AI extraction produces a traceable `StructuredCase` with sources, confidence, gaps, conflicts and safety signals.
3. The backend validates, authenticates, versions and publishes case updates.
4. The staff dashboard shows the draft for review and correction.
5. An authorised human approves the final triage and record.

## Team workflow

1. Pick or receive a GitHub Issue.
2. Create a branch from the latest `main`:

   ```bash
   git switch main
   git pull
   git switch -c feat/issue-number-short-description
   ```

3. Keep commits focused and never commit secrets, real patient data, recordings or identifiable transcripts.
4. Push the branch and open a Pull Request linked to the Issue.
5. Obtain at least one teammate review and resolve discussions.
6. Merge using **Squash and merge**, then delete the feature branch.

Recommended branch prefixes: `feat/`, `fix/`, `docs/`, `test/`, `chore/`.

## Data and safety rules

- Use synthetic data only unless the team has approved a protected-data environment.
- Do not put patient details, voice recordings, transcripts, secrets or tokens in GitHub.
- Do not log sensitive intake content in ordinary application logs.
- Treat AI output as an unverified draft and preserve source/confidence information.
- Require server-side authorisation, encryption in transit, retention controls and an audit trail before handling real data.

## Getting started

The repository currently contains the integration contract and examples. Each role should confirm the open decisions in `contracts/TEAM_INTEGRATION_HANDOFF.md` before the API contract is frozen.

Validate the JSON examples locally (requires Python and `jsonschema`):

```bash
python scripts/validate_contracts.py
python -m unittest discover -s tests -v
python -m src.data --validate-fixtures
python -m src.data --check-supabase
python -m src.backend
python -m src.voice
```

Role 3 listens on `http://127.0.0.1:8000`. Role 1 listens on `http://127.0.0.1:8001` so the two FastAPI apps can run together. Without `ASSEMBLYAI_API_KEY`, Role 1 starts in demo mode: `POST /api/voice/handoff` and `POST /api/voice/demo-intake` still wrap turns in `intake-transcript.schema.json`, run Role 2, and ingest into Role 3.

Staff dashboard (Role 5, after `npm install`):

```bash
npm run dev
```

Open `/dashboard`. Synthetic contract examples load without the backend. To exercise live SSE and review/save, run Role 3, ingest a case with the service token (or Role 1 handoff), then connect that `caseId`. Approvals persist through Role 4; the browser never calls Supabase.

Live voice UI: `http://127.0.0.1:8001` (requires `ASSEMBLYAI_API_KEY`). After the websocket closes, the client posts sanitized turns to Role 2/3.

Role 4 talks to Supabase. Copy `.env.example` to `.env` and set `SUPABASE_URL` plus `SUPABASE_PUBLISHABLE_KEY`. The dashboard Connect dialog labels those `NEXT_PUBLIC_*` because it assumes Next.js; this repo is Python and accepts both names. Then run `supabase/migrations/20260907120000_role4_persistence.sql` in the SQL Editor so case/review/audit tables exist. Lookup already works against the existing `patients` and `history_notes` tables.

Role 2 implementation details and the provider-adapter boundary are documented
in [`src/extraction/README.md`](src/extraction/README.md). The repository makes
no external AI call and contains no provider credential; Role 3 injects the
team's chosen model adapter at deployment time.

## Project management

- **Issues**: one deliverable or decision per Issue, with an owner and acceptance criteria.
- **Milestones**: group Issues by competition checkpoint or demo release.
- **Pull Requests**: link the relevant Issue using `Closes #123` when appropriate.
- **Main branch**: always kept in a reviewable, demo-ready state.
- **ARIA Project**: the source of truth for delivery status. Use `Backlog` → `In Progress` → `In Review` → `Done`, and attach a branch, Pull Request, test result or demo evidence.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full collaboration rules.
