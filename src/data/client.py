"""Resolve Supabase credentials for the Role 4 Python backend.

The dashboard Connect dialog copies Next.js names (`NEXT_PUBLIC_*`). This
package is Python, so the preferred names are `SUPABASE_URL` and
`SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_SECRET_KEY`. Both sets are accepted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_ENV_LOADED = False


def _load_dotenv() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    for candidate in (Path(".env"), Path(__file__).resolve().parents[2] / ".env"):
        if not candidate.is_file():
            continue
        for raw in candidate.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
        break


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


@dataclass(frozen=True)
class SupabaseSettings:
    url: str
    key: str
    key_kind: str  # "secret" or "publishable"


def load_settings() -> Optional[SupabaseSettings]:
    _load_dotenv()
    url = _first_env("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    secret = _first_env("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    publishable = _first_env(
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_KEY",
        "SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    )
    if not url:
        return None
    if secret:
        return SupabaseSettings(url=url.rstrip("/"), key=secret, key_kind="secret")
    if publishable:
        return SupabaseSettings(url=url.rstrip("/"), key=publishable, key_kind="publishable")
    return None


def is_configured() -> bool:
    return load_settings() is not None


def create_supabase_client() -> Any:
    settings = load_settings()
    if not settings:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_PUBLISHABLE_KEY (or SUPABASE_SECRET_KEY). "
            "NEXT_PUBLIC_* names from the dashboard also work."
        )
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "The supabase package is required. Install with: pip install 'supabase>=2.18.1,<3'"
        ) from exc
    return create_client(settings.url, settings.key)


class SupabaseHandle:
    """Stand-in for sqlite3.Connection so Role 3 can keep calling init_db()."""

    backend = "supabase"

    def __init__(self, client: Any, settings: SupabaseSettings):
        self.client = client
        self.settings = settings

    def close(self) -> None:
        return None


def init_handle() -> SupabaseHandle:
    settings = load_settings()
    if not settings:
        raise RuntimeError("Supabase is not configured")
    return SupabaseHandle(create_supabase_client(), settings)
