# Contributing

## Before starting

- Confirm the Issue scope and acceptance criteria.
- Comment on the Issue before working on it so work is not duplicated.
- Branch from the latest `main`; do not develop directly on `main`.
- Use this repository as the product delivery location. Do not move role work to the separate `backend` or `frontend` repositories without an approved migration decision.
- Use the canonical role paths documented in `contracts/TEAM_INTEGRATION_HANDOFF.md`.

## ARIA Project status

The ARIA Project is the team status record. Every owner is responsible for keeping the assigned item current:

- `Backlog`: work has not started.
- `In Progress`: implementation has started; comment with the branch and current next step.
- `In Review`: a Pull Request is open; link it to the Issue.
- `Done`: the change is merged to `main` and completion evidence is recorded.

If work is blocked, add a dated Issue comment describing the blocker, who or what is needed, and the intended next action. Do not report a task as complete only in Discord or another chat.

## Branches and commits

Use a short branch name such as `feat/12-voice-capture` or `fix/18-reconnect-events`.

Prefer clear commits in the imperative form, for example:

- `Add structured case validation`
- `Handle stale case versions`
- `Document review event payload`

## Pull Requests

- Keep each Pull Request focused on one Issue.
- Explain what changed, how it was tested, and any safety/privacy impact.
- Include screenshots or a short recording for UI changes, using synthetic data only.
- Link the Issue and request review from the relevant role owner.
- Resolve review comments and ensure checks pass before merge.

Use **Squash and merge** unless the team agrees otherwise. Delete the branch after merging.

## Definition of done

- Acceptance criteria are met.
- Relevant tests and contract validation pass.
- No secrets, real patient data or identifiable recordings/transcripts are included.
- Documentation and examples are updated when interfaces change.
- At least one teammate has reviewed the Pull Request.
- The linked ARIA item is moved to `Done` with merge and test/demo evidence.

## Reporting security or privacy issues

Do not open a public Issue containing sensitive information. Contact the repository owner privately and provide only the minimum information required to investigate.

