"""SQLite schema, immutability triggers, and versioned migrations."""

from __future__ import annotations

import sqlite3
from typing import Any, Optional

CURRENT_SCHEMA_VERSION = 1

TABLE_SPECS = {
    "schema_migrations": (
        "version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "patients": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "public_id TEXT UNIQUE NOT NULL, "
        "phone_hash TEXT UNIQUE, "
        "phone_enc TEXT, "
        "name_enc TEXT NOT NULL, "
        "age INTEGER, "
        "conditions_enc TEXT, "
        "allergies_enc TEXT, "
        "scenario TEXT NOT NULL CHECK (scenario IN ('sufficient','missing','conflicting')), "
        "conflicting_fields_json TEXT, "
        "purged INTEGER NOT NULL DEFAULT 0, "
        "created_at TEXT NOT NULL"
    ),
    "cases": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "public_id TEXT UNIQUE NOT NULL, "
        "patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE RESTRICT, "
        "status TEXT NOT NULL DEFAULT 'open' "
        "CHECK (status IN ('open','approved','rejected','resolved','purged')), "
        "case_version INTEGER NOT NULL DEFAULT 0, "
        "urgency_score REAL DEFAULT 0.0, "
        "summary_enc TEXT, "
        "idempotency_key TEXT UNIQUE, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now')), "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "case_keys": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "case_id INTEGER UNIQUE NOT NULL REFERENCES cases(id) ON DELETE RESTRICT, "
        "case_key_enc TEXT NOT NULL, "
        "idempotency_key TEXT UNIQUE, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "sessions": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "public_id TEXT UNIQUE NOT NULL, "
        "case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE RESTRICT, "
        "transcript_ref TEXT, "
        "sentiment TEXT DEFAULT 'okay' CHECK (sentiment IN ('calm','distressed','okay')), "
        "wpm REAL DEFAULT 120.0, "
        "disfluency_count INTEGER DEFAULT 0, "
        "idempotency_key TEXT UNIQUE, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "reviews": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "public_id TEXT UNIQUE NOT NULL, "
        "case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE RESTRICT, "
        "reviewer_id TEXT NOT NULL, "
        "reviewer_role TEXT NOT NULL, "
        "decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')), "
        "base_case_version INTEGER, "
        "idempotency_key TEXT UNIQUE NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "review_payloads": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "review_id INTEGER UNIQUE NOT NULL REFERENCES reviews(id) ON DELETE RESTRICT, "
        "notes_enc TEXT, "
        "edits_json_enc TEXT, "
        "idempotency_key TEXT UNIQUE NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "approved_records": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "public_id TEXT UNIQUE NOT NULL, "
        "case_id INTEGER UNIQUE NOT NULL REFERENCES cases(id) ON DELETE RESTRICT, "
        "patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE RESTRICT, "
        "review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE RESTRICT, "
        "case_version INTEGER NOT NULL, "
        "esi_level INTEGER CHECK (esi_level IS NULL OR (esi_level BETWEEN 1 AND 5)), "
        "final_triage_code TEXT NOT NULL, "
        "final_triage_label TEXT NOT NULL, "
        "attending_clinician TEXT NOT NULL, "
        "digital_signature TEXT NOT NULL, "
        "idempotency_key TEXT UNIQUE NOT NULL, "
        "approved_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "approved_record_payloads": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "approved_record_id INTEGER UNIQUE NOT NULL REFERENCES approved_records(id) ON DELETE RESTRICT, "
        "chief_complaint_enc TEXT NOT NULL, "
        "sbar_situation_enc TEXT NOT NULL, "
        "sbar_background_enc TEXT NOT NULL, "
        "sbar_assessment_enc TEXT NOT NULL, "
        "sbar_recommendation_enc TEXT NOT NULL, "
        "triage_rationale_enc TEXT, "
        "idempotency_key TEXT UNIQUE NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ),
    "notes": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE RESTRICT, "
        "note_date TEXT NOT NULL, "
        "note_text_enc TEXT NOT NULL, "
        "idempotency_key TEXT UNIQUE, "
        "created_at TEXT NOT NULL"
    ),
    "audit_log": (
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "entity_type TEXT NOT NULL, "
        "entity_id INTEGER NOT NULL, "
        "action TEXT NOT NULL, "
        "actor_id TEXT NOT NULL, "
        "actor_role TEXT NOT NULL, "
        "details_sanitized TEXT, "
        "prev_entry_hmac TEXT NOT NULL, "
        "entry_hmac TEXT NOT NULL, "
        "idempotency_key TEXT UNIQUE NOT NULL, "
        "created_at TEXT NOT NULL"
    ),
}

IMMUTABLE_TRIGGERS = {
    "reviews": ("trg_rev_upd", "trg_rev_del"),
    "review_payloads": ("trg_rpl_upd", "trg_rpl_del"),
    "approved_records": ("trg_app_upd", "trg_app_del"),
    "approved_record_payloads": ("trg_apl_upd", "trg_apl_del"),
    "audit_log": ("trg_aud_upd", "trg_aud_del"),
}

INDEXES = (
    ("idx_patients_public", "patients(public_id)"),
    ("idx_patients_phone", "patients(phone_hash)"),
    ("idx_cases_pat", "cases(patient_id)"),
    ("idx_cases_public", "cases(public_id)"),
    ("idx_sess_case", "sessions(case_id)"),
    ("idx_rev_case", "reviews(case_id)"),
    ("idx_app_case", "approved_records(case_id)"),
    ("idx_not_pat", "notes(patient_id)"),
    ("idx_aud_ent", "audit_log(entity_type, entity_id)"),
)


def build_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")
    for table_name, columns in TABLE_SPECS.items():
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns});")

    for table, (update_name, delete_name) in IMMUTABLE_TRIGGERS.items():
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {update_name} BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} immutable'); END;"
        )
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS {delete_name} BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} immutable'); END;"
        )

    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_not_upd BEFORE UPDATE ON notes "
        "WHEN NEW.note_text_enc != '[PURGED]' "
        "BEGIN SELECT RAISE(ABORT, 'notes append-only'); END;"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_not_del BEFORE DELETE ON notes "
        "BEGIN SELECT RAISE(ABORT, 'notes append-only'); END;"
    )

    for index_name, target in INDEXES:
        conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {target};")


def get_current_migration_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)
    except sqlite3.OperationalError:
        return int(conn.execute("PRAGMA user_version").fetchone()[0] or 0)


def get_migration_history(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(
            "SELECT version, name, applied_at FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        return []


def migrate_db(conn: sqlite3.Connection, target_version: Optional[int] = None) -> int:
    current = get_current_migration_version(conn)
    if current < 1 and (target_version is None or target_version >= 1):
        build_schema(conn)
        conn.execute(
            "INSERT OR REPLACE INTO schema_migrations (version, name) VALUES (?, ?)",
            (1, "001_initial_schema"),
        )
        conn.execute("PRAGMA user_version = 1;")
        conn.commit()
        return 1
    return current
