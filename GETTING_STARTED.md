# Getting started

A step-by-step guide for anyone running this project locally for the first time. If you just want a quick reference, see the "Getting started" section in [README.md](README.md); this doc goes deeper.

## What this project does

You call a simulated ER intake line and talk to Aira, a voice AI. As you speak, it turns the conversation into a structured medical case (chief complaint, symptoms, history, allergies, safety signals, etc.) and sends it to a staff dashboard in real time, where a (simulated) clinician can review, correct, and approve it.

Nothing in this project dispatches real help or makes a real triage decision — it is a demo/training system end to end.

It's built from five pieces that run as separate processes:

| Piece | What it does | Where it lives |
|---|---|---|
| **Role 1 — Voice** | Runs the live phone-call-style conversation (AssemblyAI voice agent) | `src/voice/` |
| **Role 2 — Extraction** | Turns the raw transcript into a structured, schema-valid case using an LLM | `src/extraction/` |
| **Role 3 — Backend** | Authenticates, stores cases in memory, streams live updates (SSE), handles staff review | `src/backend/` |
| **Role 4 — Data** | Persists approved cases to a database (Supabase, or local SQLite as a fallback) | `src/data/` |
| **Role 5 — Dashboard** | The Next.js web app: the patient call screen and the staff review dashboard | `app/`, `components/` |

## Prerequisites

- **Python 3.11+**
- **Node.js 20.9+** and npm
- Optional but recommended for a full working demo:
  - An **AssemblyAI** API key (for live voice calls) — https://www.assemblyai.com
  - An **OpenRouter** API key (cheap, for DeepSeek-powered case extraction) — https://openrouter.ai — or an **OpenAI** API key instead
  - A **Supabase** project (for real persistence) — https://supabase.com

You can run the whole thing without any of the optional keys — it falls back to demo modes (no live voice, a much simpler rule-based extractor, and local SQLite instead of Supabase) — but a live end-to-end demo needs at least the AssemblyAI key.

## 1. Install dependencies

```bash
# Python dependencies for the backend and voice service
pip install -r src/voice/requirements.txt
pip install -r requirements-dev.txt

# Node dependencies for the dashboard
npm install
```

## 2. Configure your environment

Copy the example env file and fill in what you have:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Never commit `.env`. If a key is ever pushed to GitHub, remove the file from the branch and rotate/revoke every exposed key before continuing.

Before any internet-facing deployment, run `npm audit --omit=dev`. The repository is currently pinned to Next.js 16.3.4; the 10 September verification reports zero known production dependency vulnerabilities.

Open `.env` and set what applies to you:

- **Always safe to leave as-is**: the `ARIA_*` demo tokens and ports — these are fine for local dev.
- **`ASSEMBLYAI_API_KEY`** — without this, Role 1 runs in demo mode: no live call, but you can still send a canned demo transcript through the pipeline via the "Send a demo case to staff" button.
- **`OPENROUTER_API_KEY`** (recommended) or **`OPENAI_API_KEY`** — without one of these, case extraction falls back to a narrow regex-based adapter (`src/extraction/demo_adapter.py`) that only captures a handful of hardcoded symptoms/conditions. With a key set, extraction uses a real LLM and captures the full schema.
- **`SUPABASE_URL`** / **`SUPABASE_PUBLISHABLE_KEY`** (or `SUPABASE_SECRET_KEY`) — without these, `ARIA_BACKEND` should stay `sqlite` and data persists to a local file (`tmp/aria_mvp.db`) instead of Supabase. With them set, also set `ARIA_BACKEND=auto` and run the migration once (see below).

If you're using Supabase, run the migration once against your project (SQL Editor → paste and run):

```
supabase/migrations/20260907120000_role4_persistence.sql
```

You can check everything is wired correctly at any point with:

```bash
python -m src.data --check-supabase
```

The Supabase project overview does not show table contents. Use **Table Editor** to inspect `patients`, `history_notes`, `cases`, `sessions`, `reviews`, `approved_records`, and `audit_log`. “No repository connected” only means Supabase GitHub integration is not enabled; the application connects through `SUPABASE_URL` and a server-side key in your local `.env`.

## 3. Run it — three processes, three terminals

```bash
# Terminal 1 — Role 3 backend (port 8000)
python -m src.backend

# Terminal 2 — Role 1 voice service (port 8001)
python -m src.voice

# Terminal 3 — Role 5 dashboard / call UI (port 3000)
npm run dev
```

On Windows, activate the project virtual environment in each Python terminal first, or call it explicitly:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m src.backend

# Terminal 2
.\.venv\Scripts\python.exe -m src.voice

# Terminal 3
npm run dev
```

Each one logs its own health line on startup. You can sanity-check them anytime with:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/health
```

## 4. Try it

1. Open **http://localhost:3000** — the patient call screen.
2. Tap the orb and talk to Aira (or, if you don't have an AssemblyAI key, click "Send a demo case to staff" instead).
3. When the call naturally wraps up, it ends itself and hands off automatically — you'll get a short case number and a link to the staff dashboard.
4. Open **http://localhost:3000/dashboard** to see the case land, watch it fill in live, and try the review actions (save draft, request more info, approve).

For the fastest no-key smoke test, keep the three processes running and call:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/voice/demo-intake
```

The response should contain `extraction.status: success` and `ingest.httpStatus: 202`; `case_demo_001` should then appear on the dashboard.

## Troubleshooting

- **"Skipping local HTTP tools (AssemblyAI requires https://)"** in the Role 1 logs — this is expected in local dev. The voice agent has a patient-lookup tool that calls back into Role 3, but AssemblyAI's cloud can't reach `127.0.0.1`. It just means the agent won't recognize returning callers by phone; everything else still works. (Exposing Role 3 over a public HTTPS tunnel fixes this, but isn't part of the default local setup.)
- **Dashboard shows a case but most fields are empty/null** — you're probably running without `OPENROUTER_API_KEY`/`OPENAI_API_KEY` set, so extraction is using the limited regex fallback. Add one of those keys and try again.
- **Case doesn't show up in Supabase** — cases only persist to the database once the caller is linked to a known patient (matched by phone number against the 5 seeded demo patients: `9990001111`, `9990002222`, `9990003333`, `9990006666`, `9990007777`, `9990008888`). Everything else stays visible on the dashboard live but only in memory, and is lost when Role 3 restarts.
- **Voice agent starts talking over itself / says something odd** — restart `python -m src.voice`; it re-publishes the agent config (`src/voice/app/agents/emergency-voice.jsonc`) to AssemblyAI on every startup, so this also how you push prompt changes live.

## Running tests

```bash
# Python test suite
python -m unittest discover -s tests -v

# Dashboard TypeScript tests
npm run test:dashboard

# Contract examples validate against the JSON schemas
python scripts/validate_contracts.py
```
