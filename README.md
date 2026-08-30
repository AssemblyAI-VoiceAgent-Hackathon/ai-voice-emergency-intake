# AI Voice Emergency Intake

Private team repository for an AI-assisted voice intake prototype. The system is intended to capture spoken emergency-intake information, convert it into a structured case, pass it through a secure backend, and present it to authorised staff for human review.

> This prototype does not diagnose patients or make the final triage decision. A qualified human reviewer remains responsible for verification, triage and approval.

## Confirmed team roles

| Role | Team member | GitHub |
|---|---|---|
| Role 1 — Voice / conversation | Shahzaib Fraz | [@Shahzaib-Fraz](https://github.com/Shahzaib-Fraz) |
| Role 2 — AI extraction | Fazwan Zainuddin | [@fazwanproperty](https://github.com/fazwanproperty) |
| Role 3 — Backend / integration | Mozzam Shahid | [@MozzamShahid](https://github.com/MozzamShahid) |
| Role 4 — Data / persistence | Ishaan | [@IshaanSama038X](https://github.com/IshaanSama038X) |
| Role 5 — Staff dashboard / review | Jonathan | [@halojonathan](https://github.com/halojonathan) |
| Demo and presentation | Mariam | GitHub username pending |

## Current repository contents

- `contracts/structured-case.schema.json` — Role 2 structured extraction contract.
- `contracts/staff-review.schema.json` — Role 5 staff-review contract.
- `contracts/examples/` — synthetic example payloads for development and testing.
- `contracts/ROLE2_ROLE3_ROLE5_HANDOFF.md` — proposed API, event and review workflow.
- `output/pdf/AI_Emergency_Intake_Team_Workflow_Roles.pdf` — team workflow and role reference.

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

The repository currently contains the integration contract and examples. Each role should confirm the open decisions in `contracts/ROLE2_ROLE3_ROLE5_HANDOFF.md` before the API contract is frozen.

Validate the JSON examples locally (requires Python and `jsonschema`):

```bash
python scripts/validate_contracts.py
```

## Project management

- **Issues**: one deliverable or decision per Issue, with an owner and acceptance criteria.
- **Milestones**: group Issues by competition checkpoint or demo release.
- **Pull Requests**: link the relevant Issue using `Closes #123` when appropriate.
- **Main branch**: always kept in a reviewable, demo-ready state.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full collaboration rules.
