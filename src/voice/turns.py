"""Sanitize Role 1 conversation turns into the intake-transcript contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

ALLOWED_SPEAKERS = frozenset({"patient", "caregiver", "staff", "agent", "unknown"})
_SPEAKER_ALIASES = {
    "you": "patient",
    "user": "patient",
    "caller": "patient",
    "assistant": "agent",
    "aira": "agent",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sanitize_speaker(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    key = value.strip().lower()
    if key in ALLOWED_SPEAKERS:
        return key
    return _SPEAKER_ALIASES.get(key, "unknown")


def sanitize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def sanitize_spoken_at(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return _utc_now()


def sanitize_turns(raw_turns: Iterable[object] | None) -> list[dict[str, Any]]:
    """Drop incomplete turns and coerce speaker/text to contract values."""

    cleaned: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    counter = 0
    for item in raw_turns or []:
        if not isinstance(item, Mapping):
            continue
        text = sanitize_text(item.get("text"))
        if text is None:
            continue
        counter += 1
        turn_id = item.get("turnId")
        if not isinstance(turn_id, str) or not turn_id.strip() or turn_id in seen_ids:
            turn_id = f"turn_{counter}"
            while turn_id in seen_ids:
                counter += 1
                turn_id = f"turn_{counter}"
        seen_ids.add(turn_id)
        cleaned.append(
            {
                "turnId": turn_id,
                "speaker": sanitize_speaker(item.get("speaker")),
                "text": text,
                "spokenAt": sanitize_spoken_at(item.get("spokenAt")),
                "final": bool(item.get("final", True)),
            }
        )
    return cleaned
