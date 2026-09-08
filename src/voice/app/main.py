"""Talk to your agent from a browser tab.

    uvicorn app.main:app --host 0.0.0.0 --port 8000

The API key stays in this process; the page only gets 60-second tokens.
"""

from __future__ import annotations

import copy
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.routes.voice import router as voice_router  # noqa: E402
from app.core.assemblyai import (  # noqa: E402
    ApiError,
    aai,
    load_env,
    publish_agent,
    read_agent,
    required,
    stored_agent_id,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

agent_info: dict[str, str] = {"id": "", "name": "Your agent"}


def resolve_agent() -> dict[str, str]:
    """A published id means the agent is managed elsewhere, so use it as it is."""
    name = os.environ.get("AGENT", "minimal")
    known = stored_agent_id(name)
    if known:
        try:
            agent = aai(f"/agents/{known}")
        except ApiError as err:
            sys.exit(f"Could not load agent {known}: {err}")
        return {"id": known, "name": agent.get("name") or "Your agent"}
    agent = read_agent(name)
    try:
        result = publish_agent(agent, name=name, reuse_by_name=True)
    except ApiError as err:
        sys.exit(f"Could not publish app/agents/{name}.jsonc: {err}")
    verb = "Created" if result["created"] else "Updated"
    print(f'{verb} "{agent["name"]}" from app/agents/{name}.jsonc')
    return {"id": result["id"], "name": agent["name"]}


def public_agent(agent: dict) -> dict:
    """Read-only view of the stored agent. Header values and llm keys stay hidden."""
    copied = copy.deepcopy(agent)
    for tool in copied.get("tools", []):
        for header in tool.get("http", {}).get("headers", []):
            header["value"] = "<hidden>"
    for llm in copied.get("llm", []):
        llm.pop("api_key", None)
    return copied


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_env()
    required("ASSEMBLYAI_API_KEY", "get one at https://www.assemblyai.com/dashboard/api-keys")
    agent_info.update(resolve_agent())
    print(f"Agent: {agent_info['id']}")
    yield


app = FastAPI(
    title="Emergency Voice",
    description="Browser tester for an AssemblyAI Emergency Voice.",
    lifespan=lifespan,
)
app.include_router(voice_router)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/app.js")
def client_js() -> FileResponse:
    return FileResponse(STATIC_DIR / "app.js", media_type="text/javascript")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent_id": agent_info["id"], "agent_name": agent_info["name"]}


@app.get("/config")
def config() -> dict[str, str]:
    """id and name the static page needs before it loads app.js."""
    return {"id": agent_info["id"], "name": agent_info["name"]}


@app.get("/agent")
def agent() -> Any:
    try:
        stored = aai(f"/agents/{agent_info['id']}")
        return public_agent(stored)
    except ApiError as err:
        print(err)
        return JSONResponse({"error": "could not load the agent"}, status_code=502)
