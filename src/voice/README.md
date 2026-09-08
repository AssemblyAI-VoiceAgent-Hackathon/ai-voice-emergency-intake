# Role 1 — Voice / conversation capture

Issue #1: Build the synthetic voice/conversation capture path that supplies stable transcript turns to the extraction component.

This service is Role 1 in the team pipeline:

1. Capture AssemblyAI transcript turns (or accept a synthetic turn array).
2. Sanitize `speaker` / `text` so every closed-session turn matches `contracts/intake-transcript.schema.json`.
3. Run Role 2 `extract_structured_case` (demo adapter when no model is configured).
4. `POST` the StructuredCase to Role 3 at `/api/v1/cases/{caseId}/structured-case`.
5. Staff review the case on the Role 5 dashboard.

Role 1 binds to port **8001** by default so it does not collide with Role 3 on **8000**.

## Issue #1: Build the synthetic voice/conversation capture path that supplies stable transcript turns to the extraction component.

When the websocket closed, the browser could log transcript turns before validating the `speaker` and `text` values. That allowed incomplete entries to appear in the final output, such as ,check the console tab:

```js
{
  turnId: 'turn_1',
  speaker,
  text,
  spokenAt: '2026-09-08T12:34:56.789Z',
  final: true,
}
```

The client now sanitizes malformed values before pushing them into the final turn array, so closed-session transcripts always include valid fields like:

```js
{
  turnId: 'turn_1',
  speaker: 'patient',
  text: 'Hello there',
  spokenAt: '2026-09-08T12:34:56.789Z',
  final: true,
}
```

## Configuration

 ## Create a `.env` file in the project root with your AssemblyAI credentials:
    1- Generate ASSEMBLYAI_API_KEY  from https://www.assemblyai.com/dashboard/api-keys 


        ```dotenv
        ASSEMBLYAI_API_KEY=your_api_key_here 
        ```
     2- create AGENT variable 

        ```dotenv 
        AGENT=emergency-voice
        ```

     3- Publish the emergency voice agent

        From this directory, publish the agent to AssemblyAI:

            ```bash
            python -m scripts.publish
            ```

            The command reads `AGENT=emergency-voice` and creates or updates the agent defined in `app/agents/emergency-voice.jsonc`. When a new agent is created, its ID is saved automatically in `.env` as:

            ```dotenv
            AGENT_ID_EMERGENCY_VOICE=<generated-agent-id>
            ```

            Keep this value in `.env`. Future publishes reuse that ID and update the existing agent. If the ID is missing or the agent was deleted, run the publish command again to generate a new one.

## How To Test


## Run without Docker

From the repository root (Roles 2–5 stay importable):

```bash
pip install -r requirements-dev.txt
pip install -r src/voice/requirements.txt
python -m src.backend
python -m src.voice
```

Open `http://localhost:8001` in a browser to use the voice client. Role 3 remains on `http://localhost:8000`.

Standalone (from this directory):

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Useful API endpoints:

```bash
curl http://localhost:8001/health
curl http://localhost:8001/config
curl http://localhost:8001/api/voice/token
curl -X POST http://localhost:8001/api/voice/demo-intake
```

`POST /api/voice/handoff` accepts `{ "turns": [ { "speaker", "text", "spokenAt", "final" } ] }`. Invalid speaker/text values are dropped or coerced before Role 2 sees them.

Without `ASSEMBLYAI_API_KEY` the process still starts in demo mode so the Role 2/3 handoff can be tested.

## Run with Docker

Build the image:

```bash
docker build -t emergency-voice-backend .
```

Start the container with the local environment file:

```bash
docker run --rm --env-file .env -p 8000:8000 emergency-voice-backend
```

Open `http://localhost:8000` in a browser, or check the health endpoint:

```bash
curl http://localhost:8000/health
```
