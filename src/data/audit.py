"""Append-only HMAC-chained audit log."""

from __future__ import annotations

import hmac
import hashlib
import json
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Optional

from .crypto import audit_key, derive_idempotency_key, sanitize_details

GENESIS_ROOT = "GENESIS_ROOT"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_audit(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_id: str,
    actor_role: str,
    details: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> None:
    sanitized = json.dumps(sanitize_details(details or {}), sort_keys=True)
    timestamp = utc_now()
    last = conn.execute("SELECT entry_hmac FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    prev_hmac = last["entry_hmac"] if last else GENESIS_ROOT
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "aud", entity_type, entity_id, action, actor_id, actor_role, time.time_ns(), secrets.token_hex(4)
        )
    message = (
        f"{prev_hmac}|{entity_type}|{entity_id}|{action}|{actor_id}|{actor_role}|"
        f"{sanitized}|{idempotency_key}|{timestamp}"
    )
    entry_hmac = hmac.new(audit_key(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    try:
        conn.execute(
            "INSERT INTO audit_log (entity_type, entity_id, action, actor_id, actor_role, "
            "details_sanitized, prev_entry_hmac, entry_hmac, idempotency_key, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                entity_type,
                entity_id,
                action,
                actor_id,
                actor_role,
                sanitized,
                prev_hmac,
                entry_hmac,
                idempotency_key,
                timestamp,
            ),
        )
    except sqlite3.IntegrityError:
        pass


def verify_audit_integrity(conn: sqlite3.Connection) -> tuple[bool, Optional[str]]:
    previous = GENESIS_ROOT
    key = audit_key()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
    for row in rows:
        if row["prev_entry_hmac"] != previous:
            return False, f"Broken chain at {row['id']}"
        message = (
            f"{row['prev_entry_hmac']}|{row['entity_type']}|{row['entity_id']}|{row['action']}|"
            f"{row['actor_id']}|{row['actor_role']}|{row['details_sanitized']}|"
            f"{row['idempotency_key']}|{row['created_at']}"
        )
        expected = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, row["entry_hmac"]):
            return False, f"Hash mismatch at entry {row['id']}"
        previous = row["entry_hmac"]
    return True, None


def get_audit_trail(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]
