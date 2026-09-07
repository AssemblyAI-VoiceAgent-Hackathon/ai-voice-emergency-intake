# Role 3 — Backend / integration

Authenticated FastAPI service for structured-case ingestion, SSE live updates,
staff-review submission, and JSON-schema tool calling. Role 5 never writes to
the database; approved saves go through Role 4.

Issues covered: #3, #17, #19.

## Routes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | none | Liveness |
| `POST` | `/api/v1/cases/{caseId}/structured-case` | service | Role 2 ingest |
| `GET` | `/api/v1/cases/{caseId}` | staff / service / dispatcher | Snapshot |
| `GET` | `/api/v1/cases/{caseId}/events` | staff / service / dispatcher | SSE |
| `POST` | `/api/v1/cases/{caseId}/reviews` | staff clinician | Role 5 review |
| `POST` | `/api/v1/cases/{caseId}/tools` | service / staff | `lookup_patient` |
| `GET` | `/api/v1/patients/lookup` | staff / service | Authorised Role 4 lookup |

SSE events: `case.snapshot`, `case.updated`, `case.tool_status`, `case.review_status`.
Reconnect with `Last-Event-ID`. Duplicate `Idempotency-Key` values return the original result. Stale `caseVersion` / `baseCaseVersion` returns `409`.

Demo bearer tokens (override in `.env`):

- `ARIA_SERVICE_TOKEN` default `service-demo-token` — Role 2 ingest / tools
- `ARIA_STAFF_TOKEN` default `staff-demo-token` — clinician review
- `ARIA_DISPATCHER_TOKEN` default `dispatcher-demo-token` — redacted read only

Reviewer identity is taken from the token, never from the request body.

```bash
python -m pip install -r requirements-dev.txt
python -m src.backend
```

```bash
curl -s -H "Authorization: Bearer service-demo-token" ^
  -H "Idempotency-Key: case_demo_sufficient-1" ^
  -H "Content-Type: application/json" ^
  --data-binary @contracts/examples/structured-case.sufficient.example.json ^
  http://127.0.0.1:8000/api/v1/cases/case_demo_sufficient/structured-case
```
