# AI Voice Emergency Intake

Private team repository for an AI-assisted voice intake prototype. The system is intended to capture spoken emergency-intake information, convert it into a structured case, pass it through a secure backend, and present it to authorised staff for human review.

> This prototype does not diagnose patients or make the final triage decision. A qualified human reviewer remains responsible for verification, triage and approval.

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
- `src/extraction/` — provider-neutral, schema-first extraction and safe-failure engine.
- `TEAM_PRIORITY_WORKLIST.md` — owner priorities, dependencies, integration order and first shared checkpoint.
- `output/pdf/AI_Emergency_Intake_Team_Workflow_Roles.pdf` — current team workflow (v4), confirmed role reference and Ishaan Sama contribution map.

The workflow PDF is the confirmed role reference: Soha Raees (Role 1), Fazwan Zainuddin (Role 2), Mozzam Shahid (Role 3), Ishaan Sama (Role 4), Jonathan (Role 5), and Mariam Habib (demo and presentation). It also maps Ishaan Sama's EmergencyVoice tech-stack contribution into the shared FastAPI + SSE plan.

## Repository and delivery map

This repository is the single active product repository. The organisation repositories named `backend` and `frontend` are currently empty and are not part of this delivery workflow. Do not push project work to them unless the team first approves and documents a migration.

| Owner | Delivery path in this repository |
|---|---|
| Role 1 — Soha | `src/voice/` |
| Role 2 — Fazwan | `src/extraction/` |
| Role 3 — Mozzam | `backend/` |
| Role 4 — Ishaan | `src/data/` |
| Role 5 — Jonathan | `src/dashboard/` |
| Demo — Mariam | `demo/` and `presentation/` |

A branch is a temporary version of this same repository, not a separate delivery folder. GitHub shows a branch's own snapshot: an older branch can still show an old PDF or return a 404 for a file that was added later on `main`. Only reviewed and merged work appears on `main`.

## Verified implementation snapshot — 7 September 2026

| Area | Evidence currently visible in GitHub | Interpretation |
|---|---|---|
| Shared contracts and workflow | Present on `main` | Available to all roles as the integration baseline. |
| Role 1 — Voice | `service/voice-intake` currently points to the same commit as `main`; no `src/voice/` implementation is visible on `main` | No Role 1 code delivery can yet be verified from the repository. |
| Role 2 — Extraction | `src/extraction/`, contract examples and tests are present on `main` | This is the only role implementation currently verifiable on `main`. |
| Role 3 — Backend | Work is visible on `feature/backend-voice-intake-service`, including a top-level `backend/` path | The backend work is on a feature branch and is not part of `main` until reviewed and merged. |
| Roles 4 and 5 | No role implementation path is visible on `main` | Delivery cannot yet be verified from `main`. |

At the time of this snapshot, the ARIA board showed eight items in `Backlog`, three in `Done`, and none in `In Progress` or `In Review`. Team members must update their own Issue and attach evidence; this document does not infer completion from chat messages.

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
```

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
