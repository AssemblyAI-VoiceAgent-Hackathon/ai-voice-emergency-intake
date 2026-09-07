"""Authorised patient lookup, case persistence, approved-record save, and retention."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Optional

from .audit import get_audit_trail as _sqlite_get_audit_trail, log_audit, utc_now
from .audit import verify_audit_integrity as _sqlite_verify_audit_integrity
from .crypto import (
    dec_master,
    dec_with_key,
    derive_idempotency_key,
    enc_master,
    enc_with_key,
    ensure_synthetic_text,
    master_key,
    phone_hash,
    validate_synthetic_text,
)
from .fixtures import NOT_FOUND_PHONE, persistable_notes, persistable_patients, synthetic_phone_allowlist
from .rbac import Role, authorize, is_redacted_role
from .schema import get_current_migration_version, migrate_db

DEFAULT_DB_PATH = os.environ.get("ARIA_DB_PATH", os.path.join("tmp", "aria_mvp.db"))
PHONE_PATTERN = re.compile(r"^999000\d{4}$")
_AUTO = object()


def _use_supabase(conn: Any) -> bool:
    return getattr(conn, "backend", None) == "supabase"


def _dispatch(fn):
    @wraps(fn)
    def wrapped(conn, *args, **kwargs):
        if _use_supabase(conn):
            from . import supabase_store

            return getattr(supabase_store, fn.__name__)(conn, *args, **kwargs)
        return fn(conn, *args, **kwargs)

    return wrapped


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Any = _AUTO) -> Any:
    """Open Supabase when configured, otherwise the local SQLite file.

    Passing an explicit path (including ``:memory:``) always uses SQLite so
    unit tests stay offline.
    """
    if db_path is _AUTO:
        backend = os.environ.get("ARIA_BACKEND", "auto").strip().lower()
        if backend != "sqlite":
            from .client import is_configured
            from .supabase_store import init_db as init_supabase

            if is_configured():
                return init_supabase()
        db_path = DEFAULT_DB_PATH
    conn = get_connection(str(db_path))
    migrate_db(conn)
    return conn


def verify_audit_integrity(conn: Any) -> tuple[bool, Optional[str]]:
    if _use_supabase(conn):
        from . import supabase_store

        return supabase_store.verify_audit_integrity(conn)
    return _sqlite_verify_audit_integrity(conn)


def get_audit_trail(conn: Any, limit: int = 50) -> list[dict[str, Any]]:
    if _use_supabase(conn):
        from . import supabase_store

        return supabase_store._select(conn, "audit_log", order=("id", True), limit=limit)
    return _sqlite_get_audit_trail(conn, limit)


def _public_from_idempotency(prefix: str, idempotency_key: str) -> str:
    return f"{prefix}_{idempotency_key[-16:]}"


def _case_key(conn: sqlite3.Connection, case_id: int) -> Optional[bytes]:
    row = conn.execute("SELECT case_key_enc FROM case_keys WHERE case_id=?", (case_id,)).fetchone()
    if not row:
        return None
    raw = dec_master(row["case_key_enc"])
    if not raw or raw in ("[PURGED]", "[REDACTED]", "[ERROR]", "[INVALID]"):
        return None
    try:
        return base64.b64decode(raw)
    except (ValueError, TypeError):
        return None


def _ensure_case_key(conn: sqlite3.Connection, case_id: int) -> None:
    if conn.execute("SELECT 1 FROM case_keys WHERE case_id=?", (case_id,)).fetchone():
        return
    encoded = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
    try:
        conn.execute(
            "INSERT INTO case_keys (case_id, case_key_enc, idempotency_key) VALUES (?,?,?)",
            (case_id, enc_master(encoded), derive_idempotency_key("ckey", case_id)),
        )
    except sqlite3.IntegrityError:
        pass


def enc_case(conn: sqlite3.Connection, case_id: int, text: Optional[str]) -> Optional[str]:
    key = _case_key(conn, case_id)
    if not key:
        raise RuntimeError("Missing case encryption key")
    return enc_with_key(key, text)


def dec_case(conn: sqlite3.Connection, case_id: int, ciphertext: Optional[str]) -> Optional[str]:
    key = _case_key(conn, case_id)
    return "[PURGED]" if not key else dec_with_key(key, ciphertext)


@_dispatch
def seed_synthetic_data(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0] > 0:
        return
    mapping: dict[int, int] = {}
    for patient in persistable_patients():
        hashed = phone_hash(patient.phone_number) if patient.phone_number else None
        cursor = conn.execute(
            "INSERT INTO patients (public_id, phone_hash, phone_enc, name_enc, age, "
            "conditions_enc, allergies_enc, scenario, conflicting_fields_json, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                patient.public_id,
                hashed,
                enc_master(patient.phone_number) if patient.phone_number else None,
                enc_master(patient.name),
                patient.age,
                enc_master(patient.known_conditions) if patient.known_conditions else None,
                enc_master(patient.known_allergies) if patient.known_allergies else None,
                patient.scenario,
                json.dumps(patient.conflicting_fields, sort_keys=True) if patient.conflicting_fields else None,
                patient.created_at,
            ),
        )
        mapping[patient.id] = cursor.lastrowid
    for note in persistable_notes():
        conn.execute(
            "INSERT INTO notes (patient_id, note_date, note_text_enc, created_at) VALUES (?,?,?,?)",
            (mapping[note.patient_id], note.note_date, enc_master(note.note_text), note.created_at),
        )
    conn.commit()


def _normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-+()]", "", str(phone))


def _is_demo_phone(phone: str) -> bool:
    clean = _normalize_phone(phone)
    return bool(PHONE_PATTERN.match(clean)) and clean in synthetic_phone_allowlist()


@_dispatch
def create_case_authorised(
    conn: sqlite3.Connection,
    phone: str,
    urgency_score: float = 0.0,
    summary: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    actor_id: str = "agent_01",
    actor_role: str = Role.AGENT_SYSTEM,
    public_id: Optional[str] = None,
    case_version: int = 0,
) -> dict[str, Any]:
    authorize(actor_role, "create_case")
    summary = ensure_synthetic_text(summary)
    validate_synthetic_text(summary, required=False)
    patient = conn.execute("SELECT id, public_id FROM patients WHERE phone_hash=?", (phone_hash(phone),)).fetchone()
    if not patient:
        return {"error": "Patient not found"}
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "case", patient["id"], summary, urgency_score, public_id, case_version
        )
    public_id = public_id or _public_from_idempotency("case", idempotency_key)
    try:
        cursor = conn.execute(
            "INSERT INTO cases (public_id, patient_id, urgency_score, summary_enc, "
            "idempotency_key, case_version) VALUES (?,?,?,?,?,?)",
            (public_id, patient["id"], urgency_score, enc_master(summary), idempotency_key, case_version),
        )
        case_id = cursor.lastrowid
        _ensure_case_key(conn, case_id)
        log_audit(
            conn,
            "case",
            case_id,
            "created",
            actor_id,
            actor_role,
            {"urgency": urgency_score, "public_id": public_id},
            derive_idempotency_key("aud_c", idempotency_key),
        )
        conn.commit()
        return {
            "status": "created",
            "case_id": case_id,
            "case_public_id": public_id,
            "patient_id": patient["id"],
            "patient_public_id": patient["public_id"],
        }
    except sqlite3.IntegrityError:
        conn.rollback()
        existing = conn.execute(
            "SELECT id, public_id FROM cases WHERE idempotency_key=? OR public_id=?",
            (idempotency_key, public_id),
        ).fetchone()
        if existing:
            _ensure_case_key(conn, existing["id"])
            conn.commit()
        return {
            "status": "duplicate",
            "case_id": existing["id"] if existing else None,
            "case_public_id": existing["public_id"] if existing else public_id,
            "patient_id": patient["id"],
            "patient_public_id": patient["public_id"],
        }


@_dispatch
def create_session_authorised(
    conn: sqlite3.Connection,
    case_id: Optional[int] = None,
    sentiment: str = "okay",
    wpm: float = 120.0,
    disfluency_count: int = 0,
    transcript_ref: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    actor_id: str = "agent_01",
    actor_role: str = Role.AGENT_SYSTEM,
    public_id: Optional[str] = None,
    case_public_id: Optional[str] = None,
) -> dict[str, Any]:
    authorize(actor_role, "create_session")
    transcript_ref = ensure_synthetic_text(transcript_ref)
    validate_synthetic_text(transcript_ref, required=False)
    case_row = _resolve_case(conn, case_id, case_public_id)
    if not case_row:
        return {"error": "Case not found"}
    case_id = int(case_row["id"])
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "sess", case_id, sentiment, wpm, disfluency_count, transcript_ref, public_id
        )
    public_id = public_id or _public_from_idempotency("session", idempotency_key)
    try:
        cursor = conn.execute(
            "INSERT INTO sessions (public_id, case_id, transcript_ref, sentiment, wpm, "
            "disfluency_count, idempotency_key) VALUES (?,?,?,?,?,?,?)",
            (public_id, case_id, transcript_ref, sentiment, wpm, disfluency_count, idempotency_key),
        )
        session_id = cursor.lastrowid
        log_audit(
            conn,
            "session",
            session_id,
            "created",
            actor_id,
            actor_role,
            {"wpm": wpm, "public_id": public_id},
            derive_idempotency_key("aud_s", idempotency_key),
        )
        conn.commit()
        return {"status": "created", "session_id": session_id, "session_public_id": public_id, "case_id": case_id}
    except sqlite3.IntegrityError:
        conn.rollback()
        existing = conn.execute(
            "SELECT id, public_id FROM sessions WHERE idempotency_key=? OR public_id=?",
            (idempotency_key, public_id),
        ).fetchone()
        return {
            "status": "duplicate",
            "session_id": existing["id"] if existing else None,
            "session_public_id": existing["public_id"] if existing else public_id,
            "case_id": case_id,
        }


@_dispatch
def append_note_authorised(
    conn: sqlite3.Connection,
    phone: str,
    note_date: str,
    note_text: str,
    idempotency_key: Optional[str] = None,
    actor_id: str = "agent_01",
    actor_role: str = Role.AGENT_SYSTEM,
) -> dict[str, Any]:
    authorize(actor_role, "append_note")
    note_text = ensure_synthetic_text(note_text) or ""
    validate_synthetic_text(note_text, required=True)
    patient = conn.execute("SELECT id FROM patients WHERE phone_hash=?", (phone_hash(phone),)).fetchone()
    if not patient:
        return {"error": "Patient not found"}
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "note", patient["id"], note_date, hashlib.sha256(note_text.encode("utf-8")).hexdigest()[:12]
        )
    try:
        cursor = conn.execute(
            "INSERT INTO notes (patient_id, note_date, note_text_enc, idempotency_key, created_at) "
            "VALUES (?,?,?,?,?)",
            (patient["id"], note_date, enc_master(note_text), idempotency_key, utc_now()),
        )
        note_id = cursor.lastrowid
        log_audit(
            conn,
            "note",
            note_id,
            "appended",
            actor_id,
            actor_role,
            {"patient_id": patient["id"]},
            derive_idempotency_key("aud_n", idempotency_key),
        )
        conn.commit()
        return {"status": "created", "note_id": note_id, "patient_id": patient["id"]}
    except sqlite3.IntegrityError:
        conn.rollback()
        existing = conn.execute("SELECT id FROM notes WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        return {"status": "duplicate", "note_id": existing["id"] if existing else None, "patient_id": patient["id"]}


def _resolve_case(
    conn: sqlite3.Connection, case_id: Optional[int], case_public_id: Optional[str]
) -> Optional[sqlite3.Row]:
    if case_id:
        return conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if case_public_id:
        return conn.execute("SELECT * FROM cases WHERE public_id=?", (case_public_id,)).fetchone()
    return None


@_dispatch
def save_approved_record_authorised(
    conn: sqlite3.Connection,
    case_id: Optional[int] = None,
    esi_level: Optional[int] = None,
    chief_complaint: str = "",
    sbar_situation: str = "",
    sbar_background: str = "",
    sbar_assessment: str = "",
    sbar_recommendation: str = "",
    attending_clinician_id: str = "clinician_demo",
    actor_role: str = Role.CLINICIAN,
    notes: Optional[str] = None,
    decision: str = "approved",
    idempotency_key: Optional[str] = None,
    case_public_id: Optional[str] = None,
    final_triage_code: str = "CLINICAL_CODE_TO_BE_AGREED",
    final_triage_label: str = "Human-selected triage category",
    final_triage_rationale: Optional[str] = None,
    case_version: Optional[int] = None,
    edits: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Persist an immutable review and, on approval, a one-time approved record.

    Role 3 should pass the authenticated clinician identity, staff-review
    idempotencyKey, caseId/public id, baseCaseVersion, and finalTriage fields.
    """
    authorize(actor_role, "approve_record")
    if decision not in ("approved", "rejected"):
        return {"error": "Invalid decision"}
    if esi_level is not None and not (1 <= esi_level <= 5):
        return {"error": "Invalid ESI level"}
    if decision == "approved" and (not final_triage_code or not final_triage_label):
        return {"error": "final_triage_code and final_triage_label are required to approve"}

    complaint = ensure_synthetic_text(chief_complaint) or ""
    situation = ensure_synthetic_text(sbar_situation) or ""
    background = ensure_synthetic_text(sbar_background) or ""
    assessment = ensure_synthetic_text(sbar_assessment) or ""
    recommendation = ensure_synthetic_text(sbar_recommendation) or ""
    review_notes = ensure_synthetic_text(notes)
    rationale = ensure_synthetic_text(final_triage_rationale)
    if decision == "approved":
        for field in (complaint, situation, background, assessment, recommendation):
            validate_synthetic_text(field, required=True)
    validate_synthetic_text(review_notes, required=False)
    validate_synthetic_text(rationale, required=False)

    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "appr",
            case_id,
            case_public_id,
            esi_level,
            final_triage_code,
            hashlib.sha256(complaint.encode("utf-8")).hexdigest()[:12],
            attending_clinician_id,
            decision,
        )

    existing = conn.execute(
        "SELECT id, public_id, digital_signature FROM approved_records WHERE idempotency_key=?",
        (idempotency_key,),
    ).fetchone()
    if existing:
        return {
            "status": "duplicate",
            "approved_record_id": existing["id"],
            "approved_record_public_id": existing["public_id"],
            "digital_signature": existing["digital_signature"],
        }
    existing_review = conn.execute(
        "SELECT id, public_id, decision FROM reviews WHERE idempotency_key=?",
        (derive_idempotency_key("rev", idempotency_key),),
    ).fetchone()
    if existing_review:
        return {
            "status": "duplicate",
            "review_id": existing_review["id"],
            "review_public_id": existing_review["public_id"],
            "decision": existing_review["decision"],
        }

    case_row = _resolve_case(conn, case_id, case_public_id)
    if not case_row:
        return {"error": "Case not found"}
    case_id = int(case_row["id"])
    if case_row["status"] in ("approved", "rejected", "purged"):
        return {"error": f"Case is already in state '{case_row['status']}'"}

    version_at_approval = case_version if case_version is not None else int(case_row["case_version"])
    _ensure_case_key(conn, case_id)
    signature = hmac.new(
        master_key(),
        f"{case_id}:{esi_level}:{final_triage_code}:{attending_clinician_id}:{idempotency_key}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    review_public_id = _public_from_idempotency("review", idempotency_key)
    approved_public_id = _public_from_idempotency("approved", idempotency_key)

    try:
        review_id = conn.execute(
            "INSERT INTO reviews (public_id, case_id, reviewer_id, reviewer_role, decision, "
            "base_case_version, idempotency_key) VALUES (?,?,?,?,?,?,?)",
            (
                review_public_id,
                case_id,
                attending_clinician_id,
                actor_role,
                decision,
                version_at_approval,
                derive_idempotency_key("rev", idempotency_key),
            ),
        ).lastrowid
        edits_payload = json.dumps(edits, sort_keys=True) if edits else None
        conn.execute(
            "INSERT INTO review_payloads (review_id, notes_enc, edits_json_enc, idempotency_key) "
            "VALUES (?,?,?,?)",
            (
                review_id,
                enc_case(conn, case_id, review_notes),
                enc_case(conn, case_id, edits_payload) if edits_payload else None,
                derive_idempotency_key("rpl", idempotency_key),
            ),
        )

        approved_id = None
        if decision == "approved":
            approved_id = conn.execute(
                "INSERT INTO approved_records (public_id, case_id, patient_id, review_id, case_version, "
                "esi_level, final_triage_code, final_triage_label, attending_clinician, "
                "digital_signature, idempotency_key) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    approved_public_id,
                    case_id,
                    case_row["patient_id"],
                    review_id,
                    version_at_approval,
                    esi_level,
                    final_triage_code,
                    final_triage_label,
                    attending_clinician_id,
                    signature,
                    idempotency_key,
                ),
            ).lastrowid
            conn.execute(
                "INSERT INTO approved_record_payloads (approved_record_id, chief_complaint_enc, "
                "sbar_situation_enc, sbar_background_enc, sbar_assessment_enc, "
                "sbar_recommendation_enc, triage_rationale_enc, idempotency_key) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    approved_id,
                    enc_case(conn, case_id, complaint),
                    enc_case(conn, case_id, situation),
                    enc_case(conn, case_id, background),
                    enc_case(conn, case_id, assessment),
                    enc_case(conn, case_id, recommendation),
                    enc_case(conn, case_id, rationale),
                    derive_idempotency_key("apl", idempotency_key),
                ),
            )

        conn.execute(
            "UPDATE cases SET status=?, updated_at=datetime('now') WHERE id=?",
            (decision, case_id),
        )
        log_audit(
            conn,
            "approved_record" if decision == "approved" else "review",
            approved_id or review_id,
            decision,
            attending_clinician_id,
            actor_role,
            {"esi": esi_level, "triage_code": final_triage_code, "case_version": version_at_approval},
            derive_idempotency_key("aud_a", idempotency_key),
        )
        conn.commit()
        result: dict[str, Any] = {
            "status": decision,
            "case_id": case_id,
            "case_public_id": case_row["public_id"],
            "patient_id": case_row["patient_id"],
            "review_id": review_id,
            "review_public_id": review_public_id,
        }
        if decision == "approved":
            result.update(
                {
                    "approved_record_id": approved_id,
                    "approved_record_public_id": approved_public_id,
                    "digital_signature": signature,
                }
            )
        return result
    except sqlite3.IntegrityError:
        conn.rollback()
        duplicate = conn.execute(
            "SELECT id, public_id, digital_signature FROM approved_records WHERE idempotency_key=?",
            (idempotency_key,),
        ).fetchone()
        return {
            "status": "duplicate",
            "approved_record_id": duplicate["id"] if duplicate else None,
            "approved_record_public_id": duplicate["public_id"] if duplicate else None,
            "digital_signature": duplicate["digital_signature"] if duplicate else None,
        }


def _get_approved_info(conn: sqlite3.Connection, case_id: int, redacted: bool) -> dict[str, Any]:
    record = conn.execute(
        "SELECT id, public_id, review_id, case_version, esi_level, final_triage_code, "
        "final_triage_label, attending_clinician, digital_signature, approved_at "
        "FROM approved_records WHERE case_id=?",
        (case_id,),
    ).fetchone()
    if not record:
        return {}
    if redacted:
        return {
            "approved_record_id": record["id"],
            "approved_record_public_id": record["public_id"],
            "review_id": record["review_id"],
            "esi_level": record["esi_level"],
            "final_triage_code": record["final_triage_code"],
            "final_triage_label": record["final_triage_label"],
            "approved_at": record["approved_at"],
            "digital_signature_prefix": record["digital_signature"][:16],
        }

    payload_row = conn.execute(
        "SELECT * FROM approved_record_payloads WHERE approved_record_id=?", (record["id"],)
    ).fetchone()
    payload: dict[str, Any] = {}
    if payload_row:
        complaint = dec_case(conn, case_id, payload_row["chief_complaint_enc"])
        if complaint == "[PURGED]":
            payload = {"purged": True}
        else:
            payload = {
                "purged": False,
                "chief_complaint": complaint,
                "sbar_situation": dec_case(conn, case_id, payload_row["sbar_situation_enc"]),
                "sbar_background": dec_case(conn, case_id, payload_row["sbar_background_enc"]),
                "sbar_assessment": dec_case(conn, case_id, payload_row["sbar_assessment_enc"]),
                "sbar_recommendation": dec_case(conn, case_id, payload_row["sbar_recommendation_enc"]),
                "triage_rationale": dec_case(conn, case_id, payload_row["triage_rationale_enc"]),
            }
    return {
        "approved_record_id": record["id"],
        "approved_record_public_id": record["public_id"],
        "review_id": record["review_id"],
        "case_version": record["case_version"],
        "esi_level": record["esi_level"],
        "final_triage_code": record["final_triage_code"],
        "final_triage_label": record["final_triage_label"],
        "attending_clinician": record["attending_clinician"],
        "digital_signature": record["digital_signature"],
        "approved_at": record["approved_at"],
        "payload": payload,
    }


@_dispatch
def lookup_patient_authorised(
    conn: sqlite3.Connection,
    actor_id: str,
    actor_role: str,
    phone: Optional[str] = None,
    patient_public_id: Optional[str] = None,
) -> dict[str, Any]:
    redacted = is_redacted_role(actor_role)
    authorize(actor_role, "lookup_patient_redacted" if redacted else "lookup_patient")

    patient = None
    if phone:
        if phone == NOT_FOUND_PHONE or not _is_demo_phone(phone):
            return {"error": "Patient not found"}
        patient = conn.execute("SELECT * FROM patients WHERE phone_hash=?", (phone_hash(phone),)).fetchone()
    elif patient_public_id:
        patient = conn.execute("SELECT * FROM patients WHERE public_id=?", (patient_public_id,)).fetchone()
    else:
        return {"error": "Patient not found"}
    if not patient:
        return {"error": "Patient not found"}

    patient_id = patient["id"]
    notes = [
        {
            "note_date": row["note_date"],
            "note_text": "[REDACTED]" if redacted else dec_master(row["note_text_enc"]),
        }
        for row in conn.execute(
            "SELECT note_date, note_text_enc FROM notes WHERE patient_id=? ORDER BY note_date",
            (patient_id,),
        ).fetchall()
    ]
    cases = []
    for case_row in conn.execute(
        "SELECT id, public_id, status, case_version, urgency_score, summary_enc, created_at, updated_at "
        "FROM cases WHERE patient_id=? ORDER BY created_at DESC",
        (patient_id,),
    ).fetchall():
        item = dict(case_row)
        item["summary"] = "[REDACTED]" if redacted else dec_master(item.pop("summary_enc"))
        item["approved_record"] = _get_approved_info(conn, item["id"], redacted)
        cases.append(item)

    conflicting = None
    if patient["conflicting_fields_json"] and not redacted:
        conflicting = json.loads(patient["conflicting_fields_json"])

    log_audit(conn, "patient", patient_id, "lookup", actor_id, actor_role, {"redacted": redacted})
    conn.commit()
    return {
        "patient": {
            "id": patient_id,
            "public_id": patient["public_id"],
            "age": patient["age"],
            "purged": bool(patient["purged"]),
            "scenario": patient["scenario"],
            "name": "[NAME_REDACTED]" if redacted else dec_master(patient["name_enc"]),
            "phone": "[PHONE_REDACTED]" if redacted else dec_master(patient["phone_enc"]),
            "conditions": "[CONDITIONS_REDACTED]" if redacted else dec_master(patient["conditions_enc"]),
            "allergies": "[ALLERGIES_REDACTED]" if redacted else dec_master(patient["allergies_enc"]),
            "conflicting_fields": conflicting if not redacted else None,
        },
        "notes": notes,
        "cases": cases,
    }


@_dispatch
def read_case_authorised(
    conn: sqlite3.Connection,
    actor_id: str,
    actor_role: str,
    case_id: Optional[int] = None,
    case_public_id: Optional[str] = None,
) -> dict[str, Any]:
    authorize(actor_role, "read_case")
    case_row = _resolve_case(conn, case_id, case_public_id)
    if not case_row:
        return {"error": "Case not found"}
    out = {
        "id": case_row["id"],
        "public_id": case_row["public_id"],
        "patient_id": case_row["patient_id"],
        "status": case_row["status"],
        "case_version": case_row["case_version"],
        "urgency_score": case_row["urgency_score"],
        "created_at": case_row["created_at"],
        "updated_at": case_row["updated_at"],
        "summary": "[REDACTED]",
        "approved_record": _get_approved_info(conn, case_row["id"], redacted=True),
    }
    log_audit(conn, "case", case_row["id"], "read", actor_id, actor_role, {"redacted": True})
    conn.commit()
    return out


@_dispatch
def get_case_lineage(conn: sqlite3.Connection, case_id: int) -> Optional[dict[str, Any]]:
    """Internal debug helper. Does not decrypt approved clinical payloads for export."""
    case_row = conn.execute(
        "SELECT id, public_id, patient_id, status, case_version, urgency_score, created_at, updated_at "
        "FROM cases WHERE id=?",
        (case_id,),
    ).fetchone()
    if not case_row:
        return None
    patient = conn.execute(
        "SELECT id, public_id, phone_hash, age, scenario, purged FROM patients WHERE id=?",
        (case_row["patient_id"],),
    ).fetchone()
    sessions = [
        dict(row)
        for row in conn.execute(
            "SELECT id, public_id, sentiment, wpm, disfluency_count, transcript_ref, created_at "
            "FROM sessions WHERE case_id=? ORDER BY created_at ASC",
            (case_id,),
        ).fetchall()
    ]
    reviews = [
        dict(row)
        for row in conn.execute(
            "SELECT id, public_id, reviewer_id, reviewer_role, decision, base_case_version, created_at "
            "FROM reviews WHERE case_id=? ORDER BY created_at ASC",
            (case_id,),
        ).fetchall()
    ]
    approved = _get_approved_info(conn, case_id, redacted=True)
    return {
        "case": dict(case_row),
        "patient": dict(patient) if patient else None,
        "sessions": sessions,
        "reviews": reviews,
        "approved_record": approved or None,
    }


@_dispatch
def read_audit_authorised(
    conn: sqlite3.Connection, actor_id: str, actor_role: str, limit: int = 200
) -> list[dict[str, Any]]:
    authorize(actor_role, "read_audit")
    rows = get_audit_trail(conn, limit)
    log_audit(conn, "audit_log", 0, "read", actor_id, actor_role, {"limit": limit})
    conn.commit()
    return rows


@_dispatch
def purge_retention_authorised(
    conn: sqlite3.Connection,
    retention_days: int = 90,
    actor_id: str = "dpo_worker",
    actor_role: str = Role.COMPLIANCE_DPO,
) -> dict[str, Any]:
    authorize(actor_role, "purge_retention")
    cutoff = (date.today() - timedelta(days=retention_days)).isoformat()
    cases_purged = 0
    for row in conn.execute(
        "SELECT id FROM cases WHERE status='resolved' AND date(updated_at) < ?", (cutoff,)
    ).fetchall():
        case_id = row["id"]
        conn.execute(
            "UPDATE cases SET summary_enc='[PURGED]', status='purged', updated_at=datetime('now') WHERE id=?",
            (case_id,),
        )
        conn.execute("UPDATE sessions SET transcript_ref='[PURGED]' WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_keys WHERE case_id=?", (case_id,))
        log_audit(
            conn,
            "case",
            case_id,
            "purged",
            actor_id,
            actor_role,
            {"cutoff": cutoff},
            derive_idempotency_key("pcase", case_id, cutoff),
        )
        cases_purged += 1

    patients_purged = 0
    for row in conn.execute(
        """SELECT id FROM patients WHERE purged=0 AND EXISTS (SELECT 1 FROM cases WHERE patient_id=patients.id)
           AND NOT EXISTS (
               SELECT 1 FROM cases WHERE patient_id=patients.id
               AND (status NOT IN ('resolved','purged') OR (status='resolved' AND date(updated_at) >= ?))
           )""",
        (cutoff,),
    ).fetchall():
        patient_id = row["id"]
        conn.execute(
            "UPDATE patients SET phone_hash=NULL, phone_enc='[PURGED]', name_enc='[PURGED]', "
            "conditions_enc='[PURGED]', allergies_enc='[PURGED]', purged=1 WHERE id=?",
            (patient_id,),
        )
        conn.execute("UPDATE notes SET note_text_enc='[PURGED]' WHERE patient_id=?", (patient_id,))
        log_audit(
            conn,
            "patient",
            patient_id,
            "purged",
            actor_id,
            actor_role,
            {"cutoff": cutoff},
            derive_idempotency_key("ppat", patient_id, cutoff),
        )
        patients_purged += 1
    conn.commit()
    return {"purged_cases": cases_purged, "purged_patients": patients_purged, "cutoff": cutoff}


@_dispatch
def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    valid, error = verify_audit_integrity(conn)
    return {
        "patients": conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        "cases": conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
        "reviews": conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
        "approved_records": conn.execute("SELECT COUNT(*) FROM approved_records").fetchone()[0],
        "audit_entries": conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0],
        "schema_version": get_current_migration_version(conn),
        "audit_integrity": valid,
        "audit_integrity_error": error,
    }


__all__ = [
    "DEFAULT_DB_PATH",
    "Role",
    "append_note_authorised",
    "create_case_authorised",
    "create_session_authorised",
    "get_audit_trail",
    "get_case_lineage",
    "get_connection",
    "get_current_migration_version",
    "get_stats",
    "init_db",
    "lookup_patient_authorised",
    "migrate_db",
    "phone_hash",
    "purge_retention_authorised",
    "read_audit_authorised",
    "read_case_authorised",
    "save_approved_record_authorised",
    "seed_synthetic_data",
    "verify_audit_integrity",
]
