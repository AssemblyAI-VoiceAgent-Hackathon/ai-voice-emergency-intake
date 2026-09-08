# Voice AssemblyAI API Integration

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

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000` in a browser to use the voice client.

Useful API endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/config
curl http://localhost:8000/api/voice/token
```

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
