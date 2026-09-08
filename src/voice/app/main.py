"""Talk to your agent from a browser tab.

    python -m src.voice

The API key stays in this process; the page only gets 60-second tokens.
Without ASSEMBLYAI_API_KEY the service still starts in demo mode so Role 2/3
handoff can be exercised with synthetic turns.
"""

from __future__ import annotations

import copy
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

_VOICE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _VOICE_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))
if str(_VOICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_VOICE_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.routes.voice import router as voice_router  # noqa: E402
from app.core.assemblyai import (  # noqa: E402
    ApiError,
    aai,
    load_env,
    publish_agent,
    read_agent,
    stored_agent_id,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

agent_info: dict[str, str] = {"id": "", "name": "Emergency Voice", "mode": "demo"}


def demo_mode() -> bool:
    flag = os.environ.get("ARIA_VOICE_DEMO", "").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    return not os.environ.get("ASSEMBLYAI_API_KEY")


def resolve_agent() -> dict[str, str]:
    """Always publish the local agent file so prompt changes reach AssemblyAI."""
    name = os.environ.get("AGENT", "emergency-voice")
    agent = read_agent(name)
    dropped = []
    kept_tools = []
    for tool in agent.get("tools") or []:
        url = str((tool.get("http") or {}).get("url") or "")
        if url.startswith("https://"):
            kept_tools.append(tool)
        else:
            dropped.append(tool.get("name") or "unnamed")
    if dropped:
        print(
            "Skipping local HTTP tools (AssemblyAI requires https://): "
            + ", ".join(dropped)
        )
    if kept_tools:
        agent["tools"] = kept_tools
    else:
        agent.pop("tools", None)
    try:
        result = publish_agent(agent, name=name, reuse_by_name=True)
    except ApiError as err:
        sys.exit(f"Could not publish app/agents/{name}.jsonc: {err}")
    verb = "Created" if result["created"] else "Updated"
    print(f'{verb} "{agent["name"]}" from app/agents/{name}.jsonc')
    return {"id": result["id"], "name": agent["name"], "mode": "live"}


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
    if demo_mode():
        agent_info.update({"id": "", "name": "Emergency Voice (demo)", "mode": "demo"})
        print("Role 1 running in demo mode. Set ASSEMBLYAI_API_KEY for a live voice session.")
    else:
        agent_info.update(resolve_agent())
        print(f"Agent: {agent_info['id']}")
    yield


app = FastAPI(
    title="Emergency Voice",
    description="Role 1 voice capture for ARIA emergency intake.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ARIA_CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {
        "status": "ok",
        "role": "1",
        "mode": agent_info.get("mode", "demo"),
        "agent_id": agent_info["id"],
        "agent_name": agent_info["name"],
    }


@app.get("/config")
def config() -> dict[str, str]:
    """id and name the static page needs before it loads app.js."""
    return {
        "id": agent_info["id"],
        "name": agent_info["name"],
        "mode": agent_info.get("mode", "demo"),
    }


@app.get("/agent")
def agent() -> Any:
    if agent_info.get("mode") == "demo" or not agent_info.get("id"):
        return {
            "name": agent_info["name"],
            "mode": "demo",
            "note": "Live AssemblyAI agent is not loaded. Demo handoff still works via POST /api/voice/handoff.",
        }
    try:
        stored = aai(f"/agents/{agent_info['id']}")
        return public_agent(stored)
    except ApiError as err:
        print(err)
        return JSONResponse({"error": "could not load the agent"}, status_code=502)
