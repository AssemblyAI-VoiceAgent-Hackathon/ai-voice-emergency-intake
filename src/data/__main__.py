"""CLI for Role 4 persistence without Role 3.

Examples:
  python -m src.data --validate-fixtures
  python -m src.data --summary
  python -m src.data api stats
  echo {\"phone\":\"9990001111\"} | python -m src.data api lookup
"""

from __future__ import annotations

import argparse
import json
import sys

from . import fixtures
from .rbac import Role
from .store import (
    create_case_authorised,
    create_session_authorised,
    get_audit_trail,
    get_stats,
    init_db,
    lookup_patient_authorised,
    purge_retention_authorised,
    save_approved_record_authorised,
    seed_synthetic_data,
    verify_audit_integrity,
)


def _print_summary() -> None:
    fixtures.load()
    store = fixtures.Store()
    print("FIXTURE SUMMARY")
    print(f"patients: {len(store.patients)}")
    for scenario in ("sufficient", "missing", "conflicting"):
        print(f"  {scenario}: {len(fixtures.get_all_patients_by_scenario(scenario))}")
    print(f"notes: {len(store.notes)}")
    print(f"not_found_phone: {fixtures.NOT_FOUND_PHONE}")


def _run_api(command: str) -> int:
    conn = init_db()
    seed_synthetic_data(conn)
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    result: dict = {}
    try:
        if command == "stats":
            result = get_stats(conn)
        elif command == "lookup":
            result = lookup_patient_authorised(
                conn,
                payload.get("actor_id", "u1"),
                payload.get("actor_role", Role.CLINICIAN),
                phone=payload.get("phone"),
                patient_public_id=payload.get("patient_public_id"),
            )
        elif command == "create_case":
            result = create_case_authorised(
                conn,
                payload.get("phone", ""),
                float(payload.get("urgency_score", 0.0)),
                payload.get("summary", ""),
                payload.get("idempotency_key"),
                payload.get("actor_id", "a1"),
                payload.get("actor_role", Role.AGENT_SYSTEM),
                public_id=payload.get("case_public_id"),
                case_version=int(payload.get("case_version", 0)),
            )
        elif command == "create_session":
            result = create_session_authorised(
                conn,
                case_id=int(payload["case_id"]) if payload.get("case_id") is not None else None,
                sentiment=payload.get("sentiment", "okay"),
                wpm=float(payload.get("wpm", 120.0)),
                disfluency_count=int(payload.get("disfluency_count", 0)),
                transcript_ref=payload.get("transcript_ref"),
                idempotency_key=payload.get("idempotency_key"),
                actor_id=payload.get("actor_id", "a1"),
                actor_role=payload.get("actor_role", Role.AGENT_SYSTEM),
                public_id=payload.get("session_public_id"),
                case_public_id=payload.get("case_public_id"),
            )
        elif command == "approve_record":
            result = save_approved_record_authorised(
                conn,
                case_id=int(payload["case_id"]) if payload.get("case_id") is not None else None,
                esi_level=int(payload["esi_level"]) if payload.get("esi_level") is not None else None,
                chief_complaint=payload.get("chief_complaint", ""),
                sbar_situation=payload.get("sbar_situation", ""),
                sbar_background=payload.get("sbar_background", ""),
                sbar_assessment=payload.get("sbar_assessment", ""),
                sbar_recommendation=payload.get("sbar_recommendation", ""),
                attending_clinician_id=payload.get("attending_clinician_id", "dr_demo"),
                actor_role=payload.get("actor_role", Role.CLINICIAN),
                notes=payload.get("notes"),
                decision=payload.get("decision", "approved"),
                idempotency_key=payload.get("idempotency_key"),
                case_public_id=payload.get("case_public_id"),
                final_triage_code=payload.get("final_triage_code", "CLINICAL_CODE_TO_BE_AGREED"),
                final_triage_label=payload.get("final_triage_label", "Human-selected triage category"),
                final_triage_rationale=payload.get("final_triage_rationale"),
                case_version=payload.get("base_case_version"),
                edits=payload.get("edits"),
            )
        elif command == "purge":
            result = purge_retention_authorised(
                conn,
                int(payload.get("retention_days", 90)),
                payload.get("actor_id", "dpo"),
                payload.get("actor_role", Role.COMPLIANCE_DPO),
            )
        elif command == "audit":
            valid, error = verify_audit_integrity(conn)
            result = {"entries": get_audit_trail(conn, 100), "integrity": valid, "error": error}
        elif command == "verify_audit":
            valid, error = verify_audit_integrity(conn)
            result = {"valid": valid, "error": error}
        else:
            result = {"error": f"Unknown cmd {command}"}
    except PermissionError as exc:
        result = {"error": str(exc), "status": "permission_denied"}
    except Exception as exc:
        result = {"error": str(exc), "status": "exception"}
    finally:
        conn.close()
    print(json.dumps(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Role 4 persistence and synthetic fixtures")
    parser.add_argument("--validate-fixtures", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--export", nargs="?", const="src/data/synthetic/records.json")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("api", nargs="?", choices=["api"])
    parser.add_argument("command", nargs="?")
    args = parser.parse_args()

    if args.reset:
        fixtures.reset()
        print("Store reset")

    if args.validate_fixtures:
        errors = fixtures.validate()
        if errors:
            print("VALIDATION FAILED")
            for error in errors:
                print(f"  {error}")
            return 1
        print("OK: fixture validations passed")

    if args.summary:
        _print_summary()

    if args.export is not None:
        fixtures.export_fixtures_to_json(args.export)
        print(f"Exported {args.export}")

    if args.api == "api":
        return _run_api(args.command or "")

    if not any([args.validate_fixtures, args.summary, args.export is not None, args.reset, args.api]):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
