"""Shared plumbing for credentials, agent files, and the AssemblyAI API."""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
AGENT_DIR = ROOT / "app" / "agents"


def load_env(path: Path = ENV_FILE) -> None:
    """Load KEY=value settings without replacing existing environment values."""
    try:
        text = path.read_text()
    except OSError:
        return
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$", line)
        if not match:
            continue
        key, raw = match.group(1), match.group(2)
        if key in os.environ:
            continue
        os.environ[key] = re.sub(r"^(['\"])(.*)\1$", r"\2", raw)


def save_env(key: str, value: str, path: Path = ENV_FILE) -> bool:
    """Save a generated setting to .env when the filesystem is writable."""
    os.environ[key] = value
    try:
        text = path.read_text()
    except OSError:
        text = ""
    line = f"{key}={value}"
    pattern = re.compile(rf"^[ \t]*{re.escape(key)}[ \t]*=.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(line, text, count=1)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
    try:
        path.write_text(text)
        return True
    except OSError:
        return False


def required(name: str, hint: str = "") -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing {name}" + (f". {hint}" if hint else ""))
    return value


def list_agents() -> list[str]:
    return sorted(path.stem for path in AGENT_DIR.glob("*.jsonc"))


def parse_jsonc(text: str) -> Any:
    """Remove JSONC comments and trailing commas before JSON parsing."""
    output: list[str] = []
    in_string = escaped = in_line_comment = in_block_comment = False
    index = 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                output.append(char)
            index += 1
            continue
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 1
            index += 1
            continue
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            index += 2
            continue
        if char in "}]":
            while output and output[-1].isspace():
                output.pop()
            if output and output[-1] == ",":
                output.pop()
        output.append(char)
        index += 1
    return json.loads("".join(output))


def _interpolate(value: Any, missing: set[str]) -> Any:
    if isinstance(value, str):
        def swap(match: re.Match) -> str:
            name = match.group(1)
            if not os.environ.get(name):
                missing.add(name)
                return match.group(0)
            return os.environ[name]

        return re.sub(r"\$\{([A-Za-z0-9_]+)\}", swap, value)
    if isinstance(value, list):
        return [_interpolate(item, missing) for item in value]
    if isinstance(value, dict):
        return {key: _interpolate(item, missing) for key, item in value.items()}
    return value


def read_agent(name: str) -> dict:
    """Read and prepare an agent file as an AssemblyAI request body."""
    path = AGENT_DIR / f"{name}.jsonc"
    if not path.exists():
        sys.exit(f"No app/agents/{name}.jsonc. Set AGENT to one of: {', '.join(list_agents())}")
    load_env(AGENT_DIR / f"{name}.env")
    missing: set[str] = set()
    agent = _interpolate(parse_jsonc(path.read_text()), missing)
    if missing:
        names = ", ".join(sorted(missing))
        sys.exit(f"app/agents/{name}.jsonc needs {names}. Add "
                 + ("them" if len(missing) > 1 else "it") + " to .env")
    return agent


class ApiError(Exception):
    def __init__(self, label: str, status: int, body: str):
        super().__init__(f"{label} failed ({status}): {body}")
        self.status = status


def _agents_api() -> str:
    return os.environ.get("AGENTS_API_BASE", "https://agents.assemblyai.com/v1")


def _request(url: str, label: str, method: str, headers: dict, data: Optional[bytes]) -> str:
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.read().decode()
    except urllib.error.HTTPError as error:
        raise ApiError(label, error.code, error.read().decode()) from None


def aai(path: str, method: str = "GET", body: Any = None, headers: Optional[dict] = None) -> Any:
    request_headers = {
        "Authorization": f"Bearer {os.environ.get('ASSEMBLYAI_API_KEY', '')}",
        "Content-Type": "application/json",
        **(headers or {}),
    }
    data = json.dumps(body).encode() if body is not None else None
    text = _request(_agents_api() + path, f"{method} {path}", method, request_headers, data)
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {}


def agent_id_key(name: str) -> str:
    return "AGENT_ID_" + re.sub(r"[^A-Z0-9]", "_", name.upper())


def stored_agent_id(name: str) -> str:
    return os.environ.get("AGENT_ID") or os.environ.get(agent_id_key(name), "")


def publish_agent(agent: dict, name: str = "", reuse_by_name: bool = False) -> dict:
    """Create or update an agent and persist its id when possible."""
    key = agent_id_key(name)
    explicit = bool(os.environ.get("AGENT_ID"))
    agent_id = stored_agent_id(name)
    if agent_id:
        try:
            current = aai(f"/agents/{agent_id}")
            if current.get("name") and current["name"] != agent.get("name"):
                print(f'Note: agent {agent_id} was "{current["name"]}"')
            aai(f"/agents/{agent_id}", method="PUT", body=agent)
            return {"id": agent_id, "created": False, "saved": True, "key": key}
        except ApiError as error:
            if error.status != 404:
                raise
            print(f"Agent {agent_id} no longer exists, creating a new one")
    if reuse_by_name:
        existing = next(
            (item for item in aai("/agents").get("agents", [])
             if item.get("name") == agent.get("name")),
            None,
        )
        if existing:
            aai(f"/agents/{existing['id']}", method="PUT", body=agent)
            return {"id": existing["id"], "created": False,
                    "saved": save_env(key, existing["id"]), "key": key}
    created = aai("/agents", method="POST", body=agent)
    saved = False if explicit else save_env(key, created["id"])
    return {"id": created["id"], "created": True, "saved": saved, "key": key}