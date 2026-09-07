from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ["ARIA_BACKEND"] = "sqlite"

from src.data import (
    NOT_FOUND_PHONE,
    Role,
    create_case_authorised,
    create_session_authorised,
    get_current_migration_version,
    get_stats,
    init_db,
    lookup_patient_authorised,
    purge_retention_authorised,
    read_audit_authorised,
    save_approved_record_authorised,
    seed_synthetic_data,
    verify_audit_integrity,
)
from src.data.store import _get_approved_info


def _memory_db() -> sqlite3.Connection:
    conn = init_db(":memory:")
    seed_synthetic_data(conn)
    return conn


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = _memory_db()

    def tearDown(self) -> None:
        self.conn.close()

    def test_schema_seed_and_migration(self) -> None:
        self.assertGreaterEqual(get_current_migration_version(self.conn), 1)
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0], 7)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0], 8)

    def test_pii_encrypted_at_rest(self) -> None:
        raw = self.conn.execute(
            "SELECT name_enc, phone_enc FROM patients WHERE public_id=?",
            ("patient_demo_001",),
        ).fetchone()
        self.assertNotIn("TEST-PATIENT", raw["name_enc"])
        self.assertNotIn("9990001111", raw["phone_enc"])

    def test_authorised_lookup_and_redaction(self) -> None:
        clinician = lookup_patient_authorised(
            self.conn, "dr_demo", Role.CLINICIAN, phone="9990001111"
        )
        dispatcher = lookup_patient_authorised(
            self.conn, "disp_demo", Role.DISPATCHER, phone="9990001111"
        )
        self.assertEqual(clinician["patient"]["name"], "TEST-PATIENT-001")
        self.assertEqual(clinician["patient"]["public_id"], "patient_demo_001")
        self.assertEqual(dispatcher["patient"]["name"], "[NAME_REDACTED]")
        self.assertEqual(dispatcher["patient"]["phone"], "[PHONE_REDACTED]")

    def test_lookup_scenarios(self) -> None:
        self.assertEqual(
            lookup_patient_authorised(self.conn, "dr", Role.CLINICIAN, phone=NOT_FOUND_PHONE),
            {"error": "Patient not found"},
        )
        missing = lookup_patient_authorised(self.conn, "dr", Role.CLINICIAN, phone="9990007777")
        self.assertIsNone(missing["patient"]["conditions"])
        self.assertEqual(missing["patient"]["scenario"], "missing")
        conflicting = lookup_patient_authorised(self.conn, "dr", Role.CLINICIAN, phone="9990006666")
        self.assertEqual(conflicting["patient"]["scenario"], "conflicting")
        self.assertIn("age", conflicting["patient"]["conflicting_fields"])
        by_id = lookup_patient_authorised(
            self.conn, "dr", Role.CLINICIAN, patient_public_id="patient_demo_004"
        )
        self.assertIsNone(by_id["patient"]["phone"])
        self.assertEqual(by_id["patient"]["scenario"], "missing")

    def test_rbac_blocks_dispatcher_approval(self) -> None:
        with self.assertRaises(PermissionError):
            save_approved_record_authorised(
                self.conn,
                case_id=1,
                esi_level=3,
                chief_complaint="SYN:x",
                sbar_situation="SYN:x",
                sbar_background="SYN:x",
                sbar_assessment="SYN:x",
                sbar_recommendation="SYN:x",
                actor_role=Role.DISPATCHER,
            )

    def test_case_session_and_idempotent_approval(self) -> None:
        created = create_case_authorised(
            self.conn,
            "9990001111",
            urgency_score=8.0,
            summary="SYN:Shortness of breath",
            public_id="case_demo_001",
            case_version=3,
        )
        self.assertEqual(created["status"], "created")
        session = create_session_authorised(
            self.conn,
            case_id=created["case_id"],
            sentiment="distressed",
            wpm=160.0,
            disfluency_count=5,
            transcript_ref="SYN:ref",
            public_id="session_demo_001",
        )
        self.assertEqual(session["status"], "created")

        approved = save_approved_record_authorised(
            self.conn,
            case_id=created["case_id"],
            esi_level=2,
            chief_complaint="SYN:Dyspnea",
            sbar_situation="SYN:Sit",
            sbar_background="SYN:Back",
            sbar_assessment="SYN:Assess",
            sbar_recommendation="SYN:Rec",
            attending_clinician_id="dr_j",
            actor_role=Role.CLINICIAN,
            idempotency_key="review-demo-001-v3",
            final_triage_code="CLINICAL_CODE_TO_BE_AGREED",
            final_triage_label="Human-selected triage category",
            final_triage_rationale="SYN:Staff rationale",
            case_version=3,
            edits=[{"op": "replace", "path": "/history/allergies", "reason": "SYN:staff"}],
        )
        duplicate = save_approved_record_authorised(
            self.conn,
            case_id=created["case_id"],
            esi_level=2,
            chief_complaint="SYN:Dyspnea",
            sbar_situation="SYN:Sit",
            sbar_background="SYN:Back",
            sbar_assessment="SYN:Assess",
            sbar_recommendation="SYN:Rec",
            attending_clinician_id="dr_j",
            actor_role=Role.CLINICIAN,
            idempotency_key="review-demo-001-v3",
        )
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(duplicate["status"], "duplicate")
        self.assertEqual(duplicate["approved_record_id"], approved["approved_record_id"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM approved_records").fetchone()[0], 1)

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE approved_records SET esi_level=1 WHERE id=?",
                (approved["approved_record_id"],),
            )

        valid, error = verify_audit_integrity(self.conn)
        self.assertTrue(valid)
        self.assertIsNone(error)

        trail = json.dumps(read_audit_authorised(self.conn, "dr_j", Role.CLINICIAN))
        self.assertNotIn("9990001111", trail)
        self.assertNotIn("TEST-PATIENT-001", trail)
        self.assertNotIn("SYN:Dyspnea", trail)

    def test_retention_crypto_shred_and_tamper(self) -> None:
        created = create_case_authorised(
            self.conn, "9990002222", summary="SYN:Follow-up", public_id="case_demo_002"
        )
        approved = save_approved_record_authorised(
            self.conn,
            case_id=created["case_id"],
            esi_level=4,
            chief_complaint="SYN:cc",
            sbar_situation="SYN:s",
            sbar_background="SYN:b",
            sbar_assessment="SYN:a",
            sbar_recommendation="SYN:r",
            attending_clinician_id="dr_j",
            idempotency_key="approve-002",
        )
        self.conn.execute(
            "UPDATE cases SET status='resolved', updated_at='2000-01-01' WHERE id=?",
            (created["case_id"],),
        )
        self.conn.commit()
        purged = purge_retention_authorised(self.conn, 0, "dpo", Role.COMPLIANCE_DPO)
        self.assertGreaterEqual(purged["purged_cases"], 1)
        payload = _get_approved_info(self.conn, created["case_id"], redacted=False)["payload"]
        self.assertTrue(payload.get("purged"))

        again = purge_retention_authorised(self.conn, 0, "dpo", Role.COMPLIANCE_DPO)
        self.assertEqual(again["purged_cases"], 0)

        self.conn.execute("DROP TRIGGER IF EXISTS trg_aud_upd;")
        last = self.conn.execute("SELECT id FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        self.conn.execute("UPDATE audit_log SET details_sanitized='{\"tamper\":1}' WHERE id=?", (last["id"],))
        tampered, _ = verify_audit_integrity(self.conn)
        self.assertFalse(tampered)
        self.assertIsNotNone(approved["digital_signature"])

    def test_file_db_survives_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "aria.db")
            conn = init_db(path)
            seed_synthetic_data(conn)
            created = create_case_authorised(conn, "9990003333", summary="SYN:Reopen", public_id="case_reopen")
            conn.close()
            reopened = init_db(path)
            row = reopened.execute(
                "SELECT public_id FROM cases WHERE id=?", (created["case_id"],)
            ).fetchone()
            self.assertEqual(row["public_id"], "case_reopen")
            self.assertEqual(get_current_migration_version(reopened), 1)
            stats = get_stats(reopened)
            self.assertTrue(stats["audit_integrity"])
            reopened.close()


if __name__ == "__main__":
    unittest.main()
