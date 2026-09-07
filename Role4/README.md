# Role 4 working notes

Implementation lives in [`src/data/`](../src/data/README.md) so it matches
CODEOWNERS (`/src/data/`) and can land as the Role 4 PR without Role 1 or Role 3.

| Issue | Objective | Code |
|---|---|---|
| #4 | Approved-case persistence and immutable review/audit history | `src/data/schema.py`, `src/data/store.py`, `src/data/supabase_store.py`, `src/data/audit.py` |
| #20 | Authorised patient lookup, approved records, audit, migrations | `src/data/store.py`, `src/data/supabase_store.py`, `src/data/rbac.py`, `src/data/crypto.py`, `supabase/migrations/` |
| #21 | Deterministic synthetic fixtures (sufficient / missing / conflicting / not-found) | `src/data/fixtures.py`, `src/data/synthetic/records.json` |

Hosted backend is the team's Supabase project. Python reads `SUPABASE_URL` and
`SUPABASE_PUBLISHABLE_KEY` (or the `NEXT_PUBLIC_*` names the dashboard copies).
SQLite is only for offline tests. See [`src/data/README.md`](../src/data/README.md).

Do not commit the earlier scratch dumps: they used real-looking personal names
and are superseded by the synthetic `TEST-PATIENT-*` records.
