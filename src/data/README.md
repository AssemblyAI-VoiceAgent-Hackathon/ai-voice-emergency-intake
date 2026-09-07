# Role 4 — Data / persistence

Supabase (Postgres) is the hosted backend. SQLite remains the offline test
double so CI and Role 3 unit tests do not need network credentials.

Authorised patient lookup, approved-case storage, and an immutable
review/audit history. Role 1 and Role 3 are not required to run or test this
package.

Issues covered: #4, #20, #21.

## Identifier ownership

| Entity | Public ID (contract / Role 3) | Storage | Owner |
|---|---|---|---|
| Patient | `patient_demo_00N` | `patients.id` + `patients.public_id` | Role 4 |
| Case | Role 3 `caseId`, e.g. `case_demo_001` | `cases.id` + `cases.public_id` | Role 3 assigns, Role 4 persists |
| Session | Role 1/3 `sessionId` | `sessions.id` + `sessions.public_id` | Role 1/3 assign, Role 4 persists |
| Review | `review_*` | `reviews.id` + `reviews.public_id` | Role 4 on save |
| Approved record | `approved_*` | `approved_records.id` + `public_id` | Role 4 on approve |

Until Role 3 exists, omit public IDs and the store derives stable values from
the idempotency key.

## Role 3 handoff (call later from FastAPI)

```python
from src.data import (
    Role,
    init_db,
    seed_synthetic_data,
    lookup_patient_authorised,
    create_case_authorised,
    create_session_authorised,
    save_approved_record_authorised,
    read_audit_authorised,
    verify_audit_integrity,
)

conn = init_db()          # Supabase when SUPABASE_URL is set, else SQLite
seed_synthetic_data(conn)  # no-op if patients already exist in Supabase

lookup_patient_authorised(conn, actor_id, Role.CLINICIAN, phone="9990001111")
# not-found: 9990009999 -> {"error": "Patient not found"}

save_approved_record_authorised(
    conn,
    case_public_id="case_demo_001",
    attending_clinician_id=authenticated_staff_id,  # do not trust the browser
    actor_role=Role.CLINICIAN,
    idempotency_key=staff_review["idempotencyKey"],
    case_version=staff_review["baseCaseVersion"],
    final_triage_code=staff_review["finalTriage"]["code"],
    final_triage_label=staff_review["finalTriage"]["label"],
    final_triage_rationale=staff_review["finalTriage"].get("rationale"),
    edits=staff_review.get("edits"),
    chief_complaint="SYN:...",
    sbar_situation="SYN:...",
    sbar_background="SYN:...",
    sbar_assessment="SYN:...",
    sbar_recommendation="SYN:...",
)
```

Retries with the same idempotency key return `"status": "duplicate"` and the
original ids. Reviews, review payloads, approved records, and the audit log
cannot be updated or deleted (SQLite triggers).

## Privacy and retention

- Phone numbers are stored as a salted blind index plus ciphertext.
- Names, conditions, allergies, notes, SBAR, and review notes are encrypted at rest.
- Approved clinical payloads use a per-case key. Retention purge deletes that
  key (crypto-shred) after resolved cases pass the TTL (default 90 days).
- Dispatcher and DPO lookups are redacted. Audit details are sanitised.
- Do not log transcripts, tokens, or decrypted patient fields.

Environment (synthetic demo defaults only):

- `SUPABASE_URL` — project URL (`https://xxxx.supabase.co`)
- `SUPABASE_PUBLISHABLE_KEY` — publishable/anon key (`sb_publishable_...`)
- `SUPABASE_SECRET_KEY` — server secret (`sb_secret_...`). Prefer this in Role 3. Never commit it and never put it in the browser.
- `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — accepted aliases. The dashboard Connect dialog copies these Next.js names; this package is Python and maps them automatically.
- `ARIA_BACKEND=sqlite` — force the local file even when Supabase env vars are set
- `ARIA_DB_PATH` — SQLite file when Supabase is not configured, default `tmp/aria_mvp.db`
- `ARIA_SECRET_KEY` — encryption and signatures
- `ARIA_BLIND_SALT` — phone blind-index salt

Copy `.env.example` to `.env`. Do not commit `.env`.

The hosted project already has `patients` and `history_notes`. Lookup works
against those tables. Cases, sessions, reviews, approved records, and the
audit log are created by running
`supabase/migrations/20260907120000_role4_persistence.sql` in the SQL Editor.

```bash
python -m src.data --check-supabase
python -m src.data api stats
echo {"phone":"9990001111"} | python -m src.data api lookup
```

## Fixtures (load / reset / validate)

Source of truth: `src/data/fixtures.py`. JSON export: `src/data/synthetic/records.json`.

| Scenario | How to get it |
|---|---|
| Sufficient | phones `9990001111`, `9990002222`, `9990003333` |
| Missing information | `patient_demo_004` (no phone), `9990007777`, `9990008888` |
| Conflicting | `9990006666` (`conflicting_fields` on clinician lookup) |
| Not found | `9990009999` |

```bash
python -m src.data --validate-fixtures
python -m src.data --summary
python -m src.data --reset
python -m src.data --export src/data/synthetic/records.json
python -m unittest discover -s tests -v
```

In Python:

```python
from src.data import load_fixtures, reset_fixtures, validate_fixtures, get_patient_by_phone

load_fixtures()
reset_fixtures()
assert validate_fixtures() == []
```

All names are `TEST-PATIENT-*`. Clinical free text uses the `SYN:` prefix.
`.db` files are gitignored; never commit real patient data.
