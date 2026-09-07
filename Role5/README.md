# Role 5 — Staff dashboard / review

Next.js staff review UI owned by Jonathan (`@halojonathan`). The app lives at
the repository root because that is the Next.js convention (`app/`,
`components/`, `lib/`).

Role 5 talks **only** to Role 3. It never writes to Supabase or SQLite.
Approved saves are Role 3 → Role 4.

Issues covered: #5, #22, #23.

## Modes

- **Synthetic (default):** renders the frozen contract examples
  (`structured-case.example.json`, sufficient, conflicting). Reviews are
  validated locally. Use this without a running backend.
- **Live Role 3:** `GET /api/v1/cases/{caseId}` + SSE
  `/api/v1/cases/{caseId}/events` with `Last-Event-ID`, and
  `POST /api/v1/cases/{caseId}/reviews`. Patient lookup goes through
  `GET /api/v1/patients/lookup` (Role 4 authorised retrieval). Duplicate
  `eventId` values and older `caseVersion` values are ignored. Staff edits
  stay on the form across live updates and `409` conflicts.

Demo staff token (override in `.env.local`):

- `NEXT_PUBLIC_ARIA_API_URL` optional; default same-origin `/role3` proxy to `http://127.0.0.1:8000`
- `NEXT_PUBLIC_ARIA_STAFF_TOKEN` default `staff-demo-token`

```bash
python -m pip install -r requirements-dev.txt
python -m src.backend

npm install
npm run dev
```

Open http://127.0.0.1:3000/dashboard. Ingest a case with the Role 3 service
token first, then connect that `caseId` from the live bar. Approving a
review stores the record through Role 4; the dashboard only shows the
Role 3 `review_status` result.

```bash
python -m unittest discover -s tests -v
npm run test:dashboard
```
