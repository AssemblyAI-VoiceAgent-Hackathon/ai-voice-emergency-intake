"""Supabase-backed persistence using the hosted Postgres Data API.

Looks up the existing `patients` / `history_notes` tables. Cases, reviews,
approved records, and the audit log require the SQL in
`supabase/migrations/20260907120000_role4_persistence.sql`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import date, timedelta
from typing import Any, Optional

from .audit import GENESIS_ROOT, utc_now
from .client import SupabaseHandle, init_handle, load_settings
from .crypto import (
    audit_key,
    dec_master,
    dec_with_key,
    derive_idempotency_key,
    enc_master,
    enc_with_key,
    ensure_synthetic_text,
    master_key,
    phone_hash,
    sanitize_details,
    validate_synthetic_text,
)
from .fixtures import NOT_FOUND_PHONE
from .rbac import Role, authorize, is_redacted_role

PHONE_PATTERN = re.compile(r"^999000\d{4}$")
REQUIRED_TABLES = (
    "patients",
    "history_notes",
    "cases",
    "case_keys",
    "sessions",
    "reviews",
    "review_payloads",
    "approved_records",
    "approved_record_payloads",
    "audit_log",
)

try:
    from postgrest.exceptions import APIError
except ImportError:  # pragma: no cover - optional until supabase is installed
    try:
        from postgrest import APIError  # type: ignore
    except ImportError:  # pragma: no cover

        class APIError(Exception):  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args)
                self.code = kwargs.get("code")
                self.message = kwargs.get("message") or (args[0] if args else "")


def init_db() -> SupabaseHandle:
    return init_handle()


def _normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-+()]", "", str(phone))


def _is_demo_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.match(_normalize_phone(phone)))


def _is_unique_violation(exc: APIError) -> bool:
    payload = getattr(exc, "args", [None])[0]
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", "") or exc)
    if isinstance(payload, dict):
        code = payload.get("code") or code
        message = str(payload.get("message") or message)
    return str(code) == "23505" or "duplicate" in message.lower()


def _table_missing(exc: APIError) -> bool:
    payload = getattr(exc, "args", [None])[0]
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", "") or exc)
    if isinstance(payload, dict):
        code = payload.get("code") or code
        message = str(payload.get("message") or message)
    return str(code) in {"PGRST205", "42P01"} or "schema cache" in message.lower()


def _missing_table_error(table: str) -> dict[str, str]:
    return {
        "error": (
            f"Supabase table '{table}' is missing. Run "
            "supabase/migrations/20260907120000_role4_persistence.sql in the SQL Editor."
        )
    }


def _select(handle: SupabaseHandle, table: str, **kwargs: Any) -> list[dict[str, Any]]:
    query = handle.client.table(table).select(kwargs.get("columns", "*"))
    for key, value in kwargs.get("eq", {}).items():
        query = query.eq(key, value)
    if kwargs.get("order"):
        column, desc = kwargs["order"]
        query = query.order(column, desc=bool(desc))
    if kwargs.get("limit") is not None:
        query = query.limit(int(kwargs["limit"]))
    try:
        return list(query.execute().data or [])
    except APIError as exc:
        if _table_missing(exc):
            raise FileNotFoundError(table) from exc
        raise


def _one(handle: SupabaseHandle, table: str, **eq: Any) -> Optional[dict[str, Any]]:
    rows = _select(handle, table, eq=eq, limit=1)
    return rows[0] if rows else None


def _insert(handle: SupabaseHandle, table: str, row: dict[str, Any]) -> dict[str, Any]:
    try:
        data = handle.client.table(table).insert(row).execute().data or []
    except APIError as exc:
        if _table_missing(exc):
            raise FileNotFoundError(table) from exc
        raise
    if not data:
        return row
    return data[0]


def _update(handle: SupabaseHandle, table: str, values: dict[str, Any], **eq: Any) -> None:
    query = handle.client.table(table).update(values)
    for key, value in eq.items():
        query = query.eq(key, value)
    try:
        query.execute()
    except APIError as exc:
        if _table_missing(exc):
            raise FileNotFoundError(table) from exc
        raise


def _delete(handle: SupabaseHandle, table: str, **eq: Any) -> None:
    query = handle.client.table(table).delete()
    for key, value in eq.items():
        query = query.eq(key, value)
    try:
        query.execute()
    except APIError as exc:
        if _table_missing(exc):
            raise FileNotFoundError(table) from exc
        raise


def _count(handle: SupabaseHandle, table: str) -> int:
    try:
        result = handle.client.table(table).select("id", count="exact").limit(1).execute()
        return int(result.count or 0)
    except APIError as exc:
        if _table_missing(exc):
            return 0
        raise


def table_status(handle: Optional[SupabaseHandle] = None) -> dict[str, Any]:
    handle = handle or init_db()
    present: list[str] = []
    missing: list[str] = []
    for table in REQUIRED_TABLES:
        try:
            handle.client.table(table).select("*").limit(1).execute()
            present.append(table)
        except APIError:
            missing.append(table)
    settings = handle.settings
    return {
        "backend": "supabase",
        "url": settings.url,
        "key_kind": settings.key_kind,
        "present": present,
        "missing": missing,
        "patients": _count(handle, "patients") if "patients" in present else 0,
        "ready_for_lookup": "patients" in present,
        "ready_for_save": not missing,
    }


def _public_from_idempotency(prefix: str, idempotency_key: str) -> str:
    return f"{prefix}_{idempotency_key[-16:]}"


def _patient_public_id(patient: dict[str, Any]) -> str:
    return patient.get("public_id") or f"patient_demo_{int(patient['id']):03d}"


def _scenario(patient: dict[str, Any]) -> str:
    if patient.get("scenario"):
        return patient["scenario"]
    if patient.get("conflicting_fields_json"):
        return "conflicting"
    if patient.get("age") is None or not patient.get("known_conditions"):
        if patient.get("phone_number") in (None, ""):
            return "missing"
        if not patient.get("known_conditions") and not patient.get("known_allergies"):
            return "missing"
    return "sufficient"


def _plain(patient: dict[str, Any], enc_key: str, plain_key: str) -> Optional[str]:
    if plain_key in patient and patient.get(plain_key) is not None:
        return patient.get(plain_key)
    if enc_key in patient:
        return dec_master(patient.get(enc_key))
    return None


def _find_patient_by_phone(handle: SupabaseHandle, phone: str) -> Optional[dict[str, Any]]:
    clean = _normalize_phone(phone)
    try:
        row = _one(handle, "patients", phone_number=clean)
        if row:
            return row
    except FileNotFoundError:
        raise
    except APIError:
        pass
    try:
        return _one(handle, "patients", phone_hash=phone_hash(clean))
    except APIError:
        return None


def _find_patient_by_public_id(handle: SupabaseHandle, public_id: str) -> Optional[dict[str, Any]]:
    try:
        row = _one(handle, "patients", public_id=public_id)
        if row:
            return row
    except APIError:
        pass
    match = re.match(r"^patient_demo_(\d+)$", public_id)
    if match:
        return _one(handle, "patients", id=int(match.group(1)))
    return None


def _notes_for_patient(handle: SupabaseHandle, patient_id: int, redacted: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table, text_key, encrypted in (
        ("history_notes", "note_text", False),
        ("notes", "note_text_enc", True),
    ):
        try:
            rows = _select(handle, table, eq={"patient_id": patient_id}, order=("note_date", False))
            out = []
            for row in rows:
                text = row.get("note_text") if not encrypted else dec_master(row.get(text_key))
                out.append(
                    {
                        "note_date": row.get("note_date"),
                        "note_text": "[REDACTED]" if redacted else text,
                    }
                )
            return out
        except (FileNotFoundError, APIError):
            continue
    return []


def _case_key(handle: SupabaseHandle, case_id: int) -> Optional[bytes]:
    try:
        row = _one(handle, "case_keys", case_id=case_id)
    except FileNotFoundError:
        return None
    if not row:
        return None
    raw = dec_master(row.get("case_key_enc"))
    if not raw or raw in ("[PURGED]", "[REDACTED]", "[ERROR]", "[INVALID]"):
        return None
    try:
        return base64.b64decode(raw)
    except (ValueError, TypeError):
        return None


def _ensure_case_key(handle: SupabaseHandle, case_id: int) -> None:
    if _one(handle, "case_keys", case_id=case_id):
        return
    encoded = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
    try:
        _insert(
            handle,
            "case_keys",
            {
                "case_id": case_id,
                "case_key_enc": enc_master(encoded),
                "idempotency_key": derive_idempotency_key("ckey", case_id),
            },
        )
    except APIError as exc:
        if not _is_unique_violation(exc):
            raise


def enc_case(handle: SupabaseHandle, case_id: int, text: Optional[str]) -> Optional[str]:
    key = _case_key(handle, case_id)
    if not key:
        raise RuntimeError("Missing case encryption key")
    return enc_with_key(key, text)


def dec_case(handle: SupabaseHandle, case_id: int, ciphertext: Optional[str]) -> Optional[str]:
    key = _case_key(handle, case_id)
    return "[PURGED]" if not key else dec_with_key(key, ciphertext)


def _log_audit(
    handle: SupabaseHandle,
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
    try:
        last_rows = _select(handle, "audit_log", columns="entry_hmac", order=("id", True), limit=1)
    except FileNotFoundError:
        return
    prev_hmac = last_rows[0]["entry_hmac"] if last_rows else GENESIS_ROOT
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "aud", entity_type, entity_id, action, actor_id, actor_role, secrets.token_hex(8)
        )
    message = (
        f"{prev_hmac}|{entity_type}|{entity_id}|{action}|{actor_id}|{actor_role}|"
        f"{sanitized}|{idempotency_key}|{timestamp}"
    )
    entry_hmac = hmac.new(audit_key(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    try:
        _insert(
            handle,
            "audit_log",
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "details_sanitized": sanitized,
                "prev_entry_hmac": prev_hmac,
                "entry_hmac": entry_hmac,
                "idempotency_key": idempotency_key,
                "created_at": timestamp,
            },
        )
    except APIError as exc:
        if not _is_unique_violation(exc):
            raise


def seed_synthetic_data(handle: SupabaseHandle) -> None:
    if _count(handle, "patients") > 0:
        return
    from .fixtures import persistable_notes, persistable_patients

    mapping: dict[int, int] = {}
    for patient in persistable_patients():
        row = _insert(
            handle,
            "patients",
            {
                "phone_number": patient.phone_number,
                "name": patient.name,
                "age": patient.age,
                "known_conditions": patient.known_conditions,
                "known_allergies": patient.known_allergies,
            },
        )
        mapping[patient.id] = int(row["id"])
    for note in persistable_notes():
        if note.patient_id not in mapping:
            continue
        try:
            _insert(
                handle,
                "history_notes",
                {
                    "patient_id": mapping[note.patient_id],
                    "note_date": note.note_date,
                    "note_text": note.note_text,
                },
            )
        except FileNotFoundError:
            break


def _resolve_case(
    handle: SupabaseHandle, case_id: Optional[int], case_public_id: Optional[str]
) -> Optional[dict[str, Any]]:
    if case_id:
        return _one(handle, "cases", id=case_id)
    if case_public_id:
        return _one(handle, "cases", public_id=case_public_id)
    return None


def create_case_authorised(
    handle: SupabaseHandle,
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
    try:
        patient = _find_patient_by_phone(handle, phone)
    except FileNotFoundError:
        return _missing_table_error("patients")
    if not patient:
        return {"error": "Patient not found"}
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "case", patient["id"], summary, urgency_score, public_id, case_version
        )
    public_id = public_id or _public_from_idempotency("case", idempotency_key)
    try:
        row = _insert(
            handle,
            "cases",
            {
                "public_id": public_id,
                "patient_id": patient["id"],
                "urgency_score": urgency_score,
                "summary_enc": enc_master(summary),
                "idempotency_key": idempotency_key,
                "case_version": case_version,
            },
        )
        case_id = int(row["id"])
        _ensure_case_key(handle, case_id)
        _log_audit(
            handle,
            "case",
            case_id,
            "created",
            actor_id,
            actor_role,
            {"urgency": urgency_score, "public_id": public_id},
            derive_idempotency_key("aud_c", idempotency_key),
        )
        return {
            "status": "created",
            "case_id": case_id,
            "case_public_id": public_id,
            "patient_id": patient["id"],
            "patient_public_id": _patient_public_id(patient),
        }
    except FileNotFoundError as exc:
        return _missing_table_error(str(exc))
    except APIError as exc:
        if not _is_unique_violation(exc):
            return {"error": str(exc)}
        existing = _one(handle, "cases", idempotency_key=idempotency_key) or _one(
            handle, "cases", public_id=public_id
        )
        if existing:
            _ensure_case_key(handle, int(existing["id"]))
        return {
            "status": "duplicate",
            "case_id": existing["id"] if existing else None,
            "case_public_id": existing["public_id"] if existing else public_id,
            "patient_id": patient["id"],
            "patient_public_id": _patient_public_id(patient),
        }


def create_session_authorised(
    handle: SupabaseHandle,
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
    try:
        case_row = _resolve_case(handle, case_id, case_public_id)
    except FileNotFoundError:
        return _missing_table_error("cases")
    if not case_row:
        return {"error": "Case not found"}
    case_id = int(case_row["id"])
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "sess", case_id, sentiment, wpm, disfluency_count, transcript_ref, public_id
        )
    public_id = public_id or _public_from_idempotency("session", idempotency_key)
    try:
        row = _insert(
            handle,
            "sessions",
            {
                "public_id": public_id,
                "case_id": case_id,
                "transcript_ref": transcript_ref,
                "sentiment": sentiment,
                "wpm": wpm,
                "disfluency_count": disfluency_count,
                "idempotency_key": idempotency_key,
            },
        )
        session_id = int(row["id"])
        _log_audit(
            handle,
            "session",
            session_id,
            "created",
            actor_id,
            actor_role,
            {"wpm": wpm, "public_id": public_id},
            derive_idempotency_key("aud_s", idempotency_key),
        )
        return {"status": "created", "session_id": session_id, "session_public_id": public_id, "case_id": case_id}
    except FileNotFoundError as exc:
        return _missing_table_error(str(exc))
    except APIError as exc:
        if not _is_unique_violation(exc):
            return {"error": str(exc)}
        existing = _one(handle, "sessions", idempotency_key=idempotency_key) or _one(
            handle, "sessions", public_id=public_id
        )
        return {
            "status": "duplicate",
            "session_id": existing["id"] if existing else None,
            "session_public_id": existing["public_id"] if existing else public_id,
            "case_id": case_id,
        }


def append_note_authorised(
    handle: SupabaseHandle,
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
    patient = _find_patient_by_phone(handle, phone)
    if not patient:
        return {"error": "Patient not found"}
    if not idempotency_key:
        idempotency_key = derive_idempotency_key(
            "note", patient["id"], note_date, hashlib.sha256(note_text.encode("utf-8")).hexdigest()[:12]
        )
    try:
        row = _insert(
            handle,
            "history_notes",
            {
                "patient_id": patient["id"],
                "note_date": note_date,
                "note_text": note_text,
            },
        )
        note_id = int(row["id"])
        _log_audit(
            handle,
            "note",
            note_id,
            "appended",
            actor_id,
            actor_role,
            {"patient_id": patient["id"]},
            derive_idempotency_key("aud_n", idempotency_key),
        )
        return {"status": "created", "note_id": note_id, "patient_id": patient["id"]}
    except FileNotFoundError as exc:
        return _missing_table_error(str(exc))
    except APIError as exc:
        return {"error": str(exc)}


def save_approved_record_authorised(
    handle: SupabaseHandle,
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

    try:
        existing = _one(handle, "approved_records", idempotency_key=idempotency_key)
    except FileNotFoundError as exc:
        return _missing_table_error(str(exc))
    if existing:
        return {
            "status": "duplicate",
            "approved_record_id": existing["id"],
            "approved_record_public_id": existing["public_id"],
            "digital_signature": existing["digital_signature"],
        }
    existing_review = _one(
        handle, "reviews", idempotency_key=derive_idempotency_key("rev", idempotency_key)
    )
    if existing_review:
        return {
            "status": "duplicate",
            "review_id": existing_review["id"],
            "review_public_id": existing_review["public_id"],
            "decision": existing_review["decision"],
        }

    case_row = _resolve_case(handle, case_id, case_public_id)
    if not case_row:
        return {"error": "Case not found"}
    case_id = int(case_row["id"])
    if case_row["status"] in ("approved", "rejected", "purged"):
        return {"error": f"Case is already in state '{case_row['status']}'"}

    version_at_approval = case_version if case_version is not None else int(case_row["case_version"])
    _ensure_case_key(handle, case_id)
    signature = hmac.new(
        master_key(),
        f"{case_id}:{esi_level}:{final_triage_code}:{attending_clinician_id}:{idempotency_key}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    review_public_id = _public_from_idempotency("review", idempotency_key)
    approved_public_id = _public_from_idempotency("approved", idempotency_key)

    try:
        review = _insert(
            handle,
            "reviews",
            {
                "public_id": review_public_id,
                "case_id": case_id,
                "reviewer_id": attending_clinician_id,
                "reviewer_role": actor_role,
                "decision": decision,
                "base_case_version": version_at_approval,
                "idempotency_key": derive_idempotency_key("rev", idempotency_key),
            },
        )
        review_id = int(review["id"])
        edits_payload = json.dumps(edits, sort_keys=True) if edits else None
        _insert(
            handle,
            "review_payloads",
            {
                "review_id": review_id,
                "notes_enc": enc_case(handle, case_id, review_notes),
                "edits_json_enc": enc_case(handle, case_id, edits_payload) if edits_payload else None,
                "idempotency_key": derive_idempotency_key("rpl", idempotency_key),
            },
        )
        approved_id = None
        if decision == "approved":
            approved = _insert(
                handle,
                "approved_records",
                {
                    "public_id": approved_public_id,
                    "case_id": case_id,
                    "patient_id": case_row["patient_id"],
                    "review_id": review_id,
                    "case_version": version_at_approval,
                    "esi_level": esi_level,
                    "final_triage_code": final_triage_code,
                    "final_triage_label": final_triage_label,
                    "attending_clinician": attending_clinician_id,
                    "digital_signature": signature,
                    "idempotency_key": idempotency_key,
                },
            )
            approved_id = int(approved["id"])
            _insert(
                handle,
                "approved_record_payloads",
                {
                    "approved_record_id": approved_id,
                    "chief_complaint_enc": enc_case(handle, case_id, complaint),
                    "sbar_situation_enc": enc_case(handle, case_id, situation),
                    "sbar_background_enc": enc_case(handle, case_id, background),
                    "sbar_assessment_enc": enc_case(handle, case_id, assessment),
                    "sbar_recommendation_enc": enc_case(handle, case_id, recommendation),
                    "triage_rationale_enc": enc_case(handle, case_id, rationale),
                    "idempotency_key": derive_idempotency_key("apl", idempotency_key),
                },
            )
        _update(handle, "cases", {"status": decision, "updated_at": utc_now()}, id=case_id)
        _log_audit(
            handle,
            "approved_record" if decision == "approved" else "review",
            approved_id or review_id,
            decision,
            attending_clinician_id,
            actor_role,
            {"esi": esi_level, "triage_code": final_triage_code, "case_version": version_at_approval},
            derive_idempotency_key("aud_a", idempotency_key),
        )
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
    except FileNotFoundError as exc:
        return _missing_table_error(str(exc))
    except APIError as exc:
        if not _is_unique_violation(exc):
            return {"error": str(exc)}
        duplicate = _one(handle, "approved_records", idempotency_key=idempotency_key)
        return {
            "status": "duplicate",
            "approved_record_id": duplicate["id"] if duplicate else None,
            "approved_record_public_id": duplicate["public_id"] if duplicate else None,
            "digital_signature": duplicate["digital_signature"] if duplicate else None,
        }


def _get_approved_info(handle: SupabaseHandle, case_id: int, redacted: bool) -> dict[str, Any]:
    try:
        record = _one(handle, "approved_records", case_id=case_id)
    except FileNotFoundError:
        return {}
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
    payload_row = _one(handle, "approved_record_payloads", approved_record_id=record["id"])
    payload: dict[str, Any] = {}
    if payload_row:
        complaint = dec_case(handle, case_id, payload_row["chief_complaint_enc"])
        if complaint == "[PURGED]":
            payload = {"purged": True}
        else:
            payload = {
                "purged": False,
                "chief_complaint": complaint,
                "sbar_situation": dec_case(handle, case_id, payload_row["sbar_situation_enc"]),
                "sbar_background": dec_case(handle, case_id, payload_row["sbar_background_enc"]),
                "sbar_assessment": dec_case(handle, case_id, payload_row["sbar_assessment_enc"]),
                "sbar_recommendation": dec_case(handle, case_id, payload_row["sbar_recommendation_enc"]),
                "triage_rationale": dec_case(handle, case_id, payload_row["triage_rationale_enc"]),
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


def lookup_patient_authorised(
    handle: SupabaseHandle,
    actor_id: str,
    actor_role: str,
    phone: Optional[str] = None,
    patient_public_id: Optional[str] = None,
) -> dict[str, Any]:
    redacted = is_redacted_role(actor_role)
    authorize(actor_role, "lookup_patient_redacted" if redacted else "lookup_patient")

    patient = None
    try:
        if phone:
            if phone == NOT_FOUND_PHONE or not _is_demo_phone(phone):
                return {"error": "Patient not found"}
            patient = _find_patient_by_phone(handle, phone)
        elif patient_public_id:
            patient = _find_patient_by_public_id(handle, patient_public_id)
        else:
            return {"error": "Patient not found"}
    except FileNotFoundError:
        return _missing_table_error("patients")
    if not patient:
        return {"error": "Patient not found"}

    patient_id = int(patient["id"])
    notes = _notes_for_patient(handle, patient_id, redacted)
    cases = []
    try:
        case_rows = _select(handle, "cases", eq={"patient_id": patient_id}, order=("created_at", True))
    except FileNotFoundError:
        case_rows = []
    for case_row in case_rows:
        item = dict(case_row)
        summary = item.pop("summary_enc", None)
        item["summary"] = "[REDACTED]" if redacted else dec_master(summary)
        item["approved_record"] = _get_approved_info(handle, int(item["id"]), redacted)
        cases.append(item)

    conflicting = None
    raw_conflict = patient.get("conflicting_fields_json")
    if raw_conflict and not redacted:
        conflicting = json.loads(raw_conflict) if isinstance(raw_conflict, str) else raw_conflict

    _log_audit(handle, "patient", patient_id, "lookup", actor_id, actor_role, {"redacted": redacted})
    return {
        "patient": {
            "id": patient_id,
            "public_id": _patient_public_id(patient),
            "age": patient.get("age"),
            "purged": bool(patient.get("purged")),
            "scenario": _scenario(patient),
            "name": "[NAME_REDACTED]" if redacted else _plain(patient, "name_enc", "name"),
            "phone": "[PHONE_REDACTED]" if redacted else _plain(patient, "phone_enc", "phone_number"),
            "conditions": "[CONDITIONS_REDACTED]"
            if redacted
            else _plain(patient, "conditions_enc", "known_conditions"),
            "allergies": "[ALLERGIES_REDACTED]"
            if redacted
            else _plain(patient, "allergies_enc", "known_allergies"),
            "conflicting_fields": conflicting if not redacted else None,
        },
        "notes": notes,
        "cases": cases,
    }


def read_case_authorised(
    handle: SupabaseHandle,
    actor_id: str,
    actor_role: str,
    case_id: Optional[int] = None,
    case_public_id: Optional[str] = None,
) -> dict[str, Any]:
    authorize(actor_role, "read_case")
    try:
        case_row = _resolve_case(handle, case_id, case_public_id)
    except FileNotFoundError:
        return _missing_table_error("cases")
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
        "approved_record": _get_approved_info(handle, int(case_row["id"]), redacted=True),
    }
    _log_audit(handle, "case", int(case_row["id"]), "read", actor_id, actor_role, {"redacted": True})
    return out


def get_case_lineage(handle: SupabaseHandle, case_id: int) -> Optional[dict[str, Any]]:
    case_row = _one(handle, "cases", id=case_id)
    if not case_row:
        return None
    patient = _one(handle, "patients", id=case_row["patient_id"])
    sessions = _select(handle, "sessions", eq={"case_id": case_id}, order=("created_at", False))
    reviews = _select(handle, "reviews", eq={"case_id": case_id}, order=("created_at", False))
    return {
        "case": {
            k: case_row.get(k)
            for k in ("id", "public_id", "patient_id", "status", "case_version", "urgency_score", "created_at", "updated_at")
        },
        "patient": {
            "id": patient.get("id") if patient else None,
            "public_id": _patient_public_id(patient) if patient else None,
            "age": patient.get("age") if patient else None,
            "scenario": _scenario(patient) if patient else None,
            "purged": bool(patient.get("purged")) if patient else None,
        },
        "sessions": [
            {k: row.get(k) for k in ("id", "public_id", "sentiment", "wpm", "disfluency_count", "transcript_ref", "created_at")}
            for row in sessions
        ],
        "reviews": [
            {
                k: row.get(k)
                for k in ("id", "public_id", "reviewer_id", "reviewer_role", "decision", "base_case_version", "created_at")
            }
            for row in reviews
        ],
        "approved_record": _get_approved_info(handle, case_id, redacted=True) or None,
    }


def read_audit_authorised(
    handle: SupabaseHandle, actor_id: str, actor_role: str, limit: int = 200
) -> list[dict[str, Any]]:
    authorize(actor_role, "read_audit")
    try:
        rows = _select(handle, "audit_log", order=("id", True), limit=limit)
    except FileNotFoundError:
        return []
    _log_audit(handle, "audit_log", 0, "read", actor_id, actor_role, {"limit": limit})
    return rows


def verify_audit_integrity(handle: SupabaseHandle) -> tuple[bool, Optional[str]]:
    try:
        rows = _select(handle, "audit_log", order=("id", False))
    except FileNotFoundError:
        return True, None
    previous = GENESIS_ROOT
    key = audit_key()
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


def purge_retention_authorised(
    handle: SupabaseHandle,
    retention_days: int = 90,
    actor_id: str = "dpo_worker",
    actor_role: str = Role.COMPLIANCE_DPO,
) -> dict[str, Any]:
    authorize(actor_role, "purge_retention")
    cutoff = (date.today() - timedelta(days=retention_days)).isoformat()
    try:
        cases = _select(handle, "cases", eq={"status": "resolved"})
    except FileNotFoundError as exc:
        return _missing_table_error(str(exc))
    cases_purged = 0
    for row in cases:
        updated = str(row.get("updated_at") or "")
        if updated[:10] >= cutoff:
            continue
        case_id = int(row["id"])
        _update(
            handle,
            "cases",
            {"summary_enc": "[PURGED]", "status": "purged", "updated_at": utc_now()},
            id=case_id,
        )
        sessions = _select(handle, "sessions", eq={"case_id": case_id})
        for session in sessions:
            _update(handle, "sessions", {"transcript_ref": "[PURGED]"}, id=session["id"])
        _delete(handle, "case_keys", case_id=case_id)
        _log_audit(
            handle,
            "case",
            case_id,
            "purged",
            actor_id,
            actor_role,
            {"cutoff": cutoff},
            derive_idempotency_key("pcase", case_id, cutoff),
        )
        cases_purged += 1
    return {"purged_cases": cases_purged, "purged_patients": 0, "cutoff": cutoff}


def get_stats(handle: SupabaseHandle) -> dict[str, Any]:
    valid, error = verify_audit_integrity(handle)
    version = 0
    try:
        rows = _select(handle, "schema_migrations", columns="version", order=("version", True), limit=1)
        if rows:
            version = int(rows[0]["version"])
    except (FileNotFoundError, APIError, KeyError, TypeError):
        version = 1 if table_status(handle)["ready_for_save"] else 0
    return {
        "backend": "supabase",
        "key_kind": handle.settings.key_kind,
        "patients": _count(handle, "patients"),
        "cases": _count(handle, "cases"),
        "sessions": _count(handle, "sessions"),
        "reviews": _count(handle, "reviews"),
        "approved_records": _count(handle, "approved_records"),
        "audit_entries": _count(handle, "audit_log"),
        "schema_version": version,
        "audit_integrity": valid,
        "audit_integrity_error": error,
        "tables": table_status(handle),
    }


def check_connection() -> dict[str, Any]:
    settings = load_settings()
    if not settings:
        return {
            "ok": False,
            "error": "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY (NEXT_PUBLIC_* names also work).",
        }
    handle = init_db()
    status = table_status(handle)
    status["ok"] = status["ready_for_lookup"]
    return status
