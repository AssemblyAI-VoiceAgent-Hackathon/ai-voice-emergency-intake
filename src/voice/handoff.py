"""Role 1 -> Role 2 -> Role 3 handoff for a closed voice session."""

from __future__ import annotations

import json
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from src.extraction import extract_structured_case
from src.extraction.demo_adapter import demo_generate
from src.extraction.openai_adapter import openai_generate
from src.voice.turns import sanitize_turns


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _short_case_id() -> str:
    """A 5-digit case reference, easy for staff and callers to say back."""
    return f"{random.randint(10000, 99999)}"


def build_intake_transcript(
    turns: list[Mapping[str, Any]] | list[dict[str, Any]],
    *,
    case_id: str | None = None,
    session_id: str | None = None,
    case_version: int = 1,
    language: str | None = "en",
    observations: list[dict[str, Any]] | None = None,
    verified_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cleaned = sanitize_turns(turns)
    if not cleaned:
        raise ValueError("No valid transcript turns were supplied.")
    return {
        "schemaVersion": "1.0.0",
        "caseId": case_id or _short_case_id(),
        "sessionId": session_id or f"session_{uuid.uuid4().hex[:12]}",
        "caseVersion": case_version,
        "capturedAt": _utc_now(),
        "language": language,
        "turns": cleaned,
        "observations": observations or [],
        "verifiedRecords": verified_records or [],
    }


def _extraction_provider() -> str:
    """Which ModelAdapter to use.

    ARIA_EXTRACTION_PROVIDER=openai|demo overrides. Otherwise: use OpenAI when
    an API key is configured (real extraction, full schema coverage), and fall
    back to the deterministic regex adapter when it is not (offline/demo).
    """

    override = os.environ.get("ARIA_EXTRACTION_PROVIDER", "").strip().lower()
    if override in ("openai", "demo"):
        return override
    has_key = any(
        os.environ.get(name)
        for name in ("ARIA_EXTRACTION_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")
    )
    return "openai" if has_key else "demo"


def extract_from_intake(intake: Mapping[str, Any]) -> Any:
    provider = _extraction_provider()
    if provider == "openai":
        default_model = "deepseek/deepseek-chat" if os.environ.get("OPENROUTER_API_KEY") else "gpt-4o-mini"
        return extract_structured_case(
            intake,
            generate=openai_generate,
            model_name=os.environ.get("ARIA_EXTRACTION_OPENAI_MODEL", default_model),
        )
    return extract_structured_case(
        intake,
        generate=demo_generate,
        model_name=os.environ.get("ARIA_EXTRACTION_MODEL", "role2-demo-adapter"),
    )


def ingest_structured_case(payload: Mapping[str, Any]) -> dict[str, Any]:
    """POST a StructuredCase to Role 3. Returns the Role 3 JSON body."""

    base = os.environ.get("ARIA_API_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("ARIA_SERVICE_TOKEN", "service-demo-token")
    case_id = payload["caseId"]
    version = payload["caseVersion"]
    url = f"{base}/api/v1/cases/{case_id}/structured-case"
    body = json.dumps(payload).encode()
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"{case_id}-{version}",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode()
            parsed = json.loads(raw) if raw else {}
            return {"httpStatus": response.status, "body": parsed}
    except HTTPError as error:
        raw = error.read().decode()
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"error": {"message": "Role 3 returned a non-JSON error."}}
        return {"httpStatus": error.code, "body": parsed}
    except URLError:
        return {
            "httpStatus": 0,
            "body": {
                "error": {
                    "code": "ROLE3_UNAVAILABLE",
                    "message": "Role 3 is not reachable.",
                }
            },
        }


def handoff_transcript(
    raw: Mapping[str, Any],
    *,
    ingest=None,
) -> dict[str, Any]:
    """Sanitize turns, extract a StructuredCase, and ingest it into Role 3."""
    ingest_fn = ingest or ingest_structured_case

    intake = build_intake_transcript(
        raw.get("turns") or [],
        case_id=raw.get("caseId"),
        session_id=raw.get("sessionId"),
        case_version=int(raw.get("caseVersion") or 1),
        language=raw.get("language", "en"),
        observations=list(raw.get("observations") or []),
        verified_records=list(raw.get("verifiedRecords") or []),
    )
    result = extract_from_intake(intake)
    response: dict[str, Any] = {
        "intake": intake,
        "extraction": result.to_dict(),
        "ingest": None,
    }
    if not result.ok or result.payload is None:
        return response
    response["ingest"] = ingest_fn(result.payload)
    return response
