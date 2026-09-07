"""Bearer-token authentication. Reviewer identity is taken from the token, never the body."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Optional

from fastapi import Request

from .errors import ApiError

SERVICE_SCOPE = "ingest"
STAFF_SCOPE = "review"
READ_SCOPE = "read"
TOOL_SCOPE = "tool"


@dataclass(frozen=True)
class Principal:
    actor_id: str
    actor_role: str
    scopes: frozenset[str]


def _token_map() -> dict[str, Principal]:
    return {
        os.environ.get("ARIA_SERVICE_TOKEN", "service-demo-token"): Principal(
            "agent_01", "AGENT_SYSTEM", frozenset({SERVICE_SCOPE, TOOL_SCOPE, READ_SCOPE})
        ),
        os.environ.get("ARIA_STAFF_TOKEN", "staff-demo-token"): Principal(
            "clinician_demo", "CLINICIAN", frozenset({STAFF_SCOPE, READ_SCOPE, TOOL_SCOPE})
        ),
        os.environ.get("ARIA_DISPATCHER_TOKEN", "dispatcher-demo-token"): Principal(
            "dispatcher_demo", "DISPATCHER", frozenset({READ_SCOPE})
        ),
    }


def _extract_bearer(request: Request) -> Optional[str]:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
        return token or None
    return None


def authenticate(request: Request) -> Principal:
    token = _extract_bearer(request)
    if not token:
        raise ApiError(401, "UNAUTHENTICATED", "Authentication is required.")
    principal = _token_map().get(token)
    if principal is None:
        raise ApiError(401, "UNAUTHENTICATED", "Authentication is required.")
    return principal


def require_scopes(principal: Principal, *scopes: str) -> None:
    if not any(scope in principal.scopes for scope in scopes):
        raise ApiError(403, "FORBIDDEN", "The authenticated role cannot perform this action.")


def new_event_id(prefix: str = "evt") -> str:
    return f"{prefix}_{secrets.token_hex(6)}"
