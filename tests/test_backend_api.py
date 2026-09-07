from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

os.environ["ARIA_BACKEND"] = "sqlite"
os.environ["ARIA_SSE_IDLE_TIMEOUT"] = "0.05"
os.environ["ARIA_TOOL_TIMEOUT_SEC"] = "0.05"

from fastapi.testclient import TestClient

from src.backend import create_app
from src.data import init_db, seed_synthetic_data

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts" / "examples"
SERVICE = {"Authorization": "Bearer service-demo-token"}
STAFF = {"Authorization": "Bearer staff-demo-token"}
DISPATCHER = {"Authorization": "Bearer dispatcher-demo-token"}


def _load(name: str) -> dict:
    with (EXAMPLES / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    current: dict = {}
    for line in text.splitlines():
        if line.startswith("id: "):
            current["id"] = line[4:]
        elif line.startswith("event: "):
            current["event"] = line[7:]
        elif line.startswith("data: "):
            current["data"] = json.loads(line[6:])
        elif line == "" and current:
            events.append(current)
            current = {}
    if current.get("event"):
        events.append(current)
    return events


class BackendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        conn = init_db(":memory:")
        seed_synthetic_data(conn)
        self.conn = conn
        self.client = TestClient(create_app(conn))
        self.case = _load("structured-case.example.json")
        self.review = _load("staff-review.example.json")

    def tearDown(self) -> None:
        self.conn.close()

    def _ingest(self, payload: dict | None = None, headers: dict | None = None) -> object:
        body = payload or self.case
        extra = {"Idempotency-Key": f"{body['caseId']}-{body['caseVersion']}"}
        extra.update(headers or SERVICE)
        return self.client.post(
            f"/api/v1/cases/{body['caseId']}/structured-case",
            json=body,
            headers=extra,
        )

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "3")

    def test_ingest_success_and_duplicate(self) -> None:
        first = self._ingest()
        self.assertEqual(first.status_code, 202, first.text)
        self.assertEqual(first.json()["status"], "accepted")
        self.assertEqual(first.json()["eventType"], "case.snapshot")
        duplicate = self._ingest()
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(duplicate.json()["status"], "accepted")
        snapshot = self.client.get("/api/v1/cases/case_demo_001", headers=STAFF)
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot.json()["caseVersion"], 3)

    def test_unauthorised_and_forbidden(self) -> None:
        missing = self.client.post("/api/v1/cases/case_demo_001/structured-case", json=self.case)
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["error"]["code"], "UNAUTHENTICATED")
        bad = self._ingest(headers={"Authorization": "Bearer no-such-token"})
        self.assertEqual(bad.status_code, 401)
        staff_ingest = self._ingest(headers={**STAFF, "Idempotency-Key": "staff-cannot-ingest"})
        self.assertEqual(staff_ingest.status_code, 403)

    def test_schema_and_malformed_validation(self) -> None:
        malformed = self.client.post(
            "/api/v1/cases/case_demo_001/structured-case",
            content="{not-json",
            headers={**SERVICE, "Content-Type": "application/json", "Idempotency-Key": "bad-json"},
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()["error"]["code"], "MALFORMED_JSON")
        invalid = dict(self.case)
        invalid.pop("summary")
        response = self._ingest(invalid, headers={**SERVICE, "Idempotency-Key": "invalid-schema"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "SCHEMA_VALIDATION_FAILED")
        self.assertTrue(response.json()["error"]["fieldErrors"])

    def test_stale_version_conflict(self) -> None:
        self.assertEqual(self._ingest().status_code, 202)
        stale = dict(self.case)
        stale["caseVersion"] = 2
        response = self._ingest(stale, headers={**SERVICE, "Idempotency-Key": "stale-v2"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "CASE_VERSION_CONFLICT")
        self.assertEqual(response.json()["error"]["latestCaseVersion"], 3)

    def test_sse_snapshot_and_reconnect(self) -> None:
        self.assertEqual(self._ingest().status_code, 202)
        with self.client.stream("GET", "/api/v1/cases/case_demo_001/events", headers=STAFF) as stream:
            text = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in stream.iter_text())
        events = _parse_sse(text)
        types = [event["event"] for event in events]
        self.assertIn("case.snapshot", types)
        last_id = events[-1]["id"]

        updated = dict(self.case)
        updated["caseVersion"] = 4
        updated["status"] = "ready_for_review"
        self.assertEqual(self._ingest(updated, headers={**SERVICE, "Idempotency-Key": "case_demo_001-4"}).status_code, 202)

        replay_headers = dict(STAFF)
        replay_headers["Last-Event-ID"] = last_id
        with self.client.stream("GET", "/api/v1/cases/case_demo_001/events", headers=replay_headers) as stream:
            replay = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in stream.iter_text())
        replay_events = _parse_sse(replay)
        self.assertTrue(any(event["event"] == "case.updated" for event in replay_events))
        self.assertFalse(any(event["id"] == last_id for event in replay_events))

    def test_review_approve_idempotent_and_dispatcher_blocked(self) -> None:
        self.assertEqual(self._ingest().status_code, 202)
        denied = self.client.post(
            "/api/v1/cases/case_demo_001/reviews",
            json=self.review,
            headers={**DISPATCHER, "Idempotency-Key": self.review["idempotencyKey"]},
        )
        self.assertEqual(denied.status_code, 403)

        approved = self.client.post(
            "/api/v1/cases/case_demo_001/reviews",
            json=self.review,
            headers={**STAFF, "Idempotency-Key": self.review["idempotencyKey"]},
        )
        self.assertEqual(approved.status_code, 202, approved.text)
        self.assertEqual(approved.json()["status"], "approve")
        self.assertEqual(approved.json()["reviewerId"], "clinician_demo")
        self.assertIn("approvedRecord", approved.json())

        duplicate = self.client.post(
            "/api/v1/cases/case_demo_001/reviews",
            json=self.review,
            headers={**STAFF, "Idempotency-Key": self.review["idempotencyKey"]},
        )
        self.assertEqual(duplicate.status_code, 202)
        self.assertEqual(duplicate.json()["approvedRecord"], approved.json()["approvedRecord"])

        stale_review = dict(self.review)
        stale_review["idempotencyKey"] = "review-stale-next"
        stale_review["baseCaseVersion"] = 3
        conflict = self.client.post(
            "/api/v1/cases/case_demo_001/reviews",
            json=stale_review,
            headers={**STAFF, "Idempotency-Key": "review-stale-next"},
        )
        self.assertEqual(conflict.status_code, 409)

    def test_staff_edits_survive_later_ai_update(self) -> None:
        self.assertEqual(self._ingest().status_code, 202)
        draft = {
            "schemaVersion": "1.0.0",
            "caseId": "case_demo_001",
            "baseCaseVersion": 3,
            "idempotencyKey": "draft-allergies",
            "action": "save_draft",
            "edits": [
                {
                    "op": "replace",
                    "path": "/history/allergies",
                    "value": [{"name": "penicillin", "status": "reported", "details": "SYN:staff", "sourceRefs": ["staff_review_01"]}],
                    "reason": "SYN:staff confirmed",
                }
            ],
        }
        saved = self.client.post(
            "/api/v1/cases/case_demo_001/reviews",
            json=draft,
            headers={**STAFF, "Idempotency-Key": "draft-allergies"},
        )
        self.assertEqual(saved.status_code, 202, saved.text)

        later = dict(self.case)
        later["caseVersion"] = 10
        later["history"] = dict(self.case["history"])
        later["history"]["allergies"] = [{"name": "allergy status", "status": "unknown", "details": None, "sourceRefs": []}]
        self.assertEqual(self._ingest(later, headers={**SERVICE, "Idempotency-Key": "ai-v10"}).status_code, 202)
        snapshot = self.client.get("/api/v1/cases/case_demo_001", headers=STAFF).json()
        self.assertEqual(snapshot["structuredCase"]["history"]["allergies"][0]["name"], "penicillin")

    def test_tool_lookup_duplicate_invalid_and_timeout(self) -> None:
        self.assertEqual(self._ingest().status_code, 202)
        ok = self.client.post(
            "/api/v1/cases/case_demo_001/tools",
            json={"tool": "lookup_patient", "arguments": {"phone": "9990001111"}, "idempotencyKey": "tool-1"},
            headers={**SERVICE, "Idempotency-Key": "tool-1"},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["status"], "success")
        self.assertEqual(ok.json()["result"]["patient"]["public_id"], "patient_demo_001")

        duplicate = self.client.post(
            "/api/v1/cases/case_demo_001/tools",
            json={"tool": "lookup_patient", "arguments": {"phone": "9990001111"}, "idempotencyKey": "tool-1"},
            headers={**SERVICE, "Idempotency-Key": "tool-1"},
        )
        self.assertTrue(duplicate.json().get("duplicate"))

        invalid = self.client.post(
            "/api/v1/cases/case_demo_001/tools",
            json={"tool": "lookup_patient", "arguments": {"phone": "1"}, "idempotencyKey": "tool-bad"},
            headers={**SERVICE, "Idempotency-Key": "tool-bad"},
        )
        self.assertEqual(invalid.status_code, 422)

        timeout = self.client.post(
            "/api/v1/cases/case_demo_001/tools",
            json={"tool": "lookup_patient", "arguments": {"simulate": "timeout"}, "idempotencyKey": "tool-timeout"},
            headers={**SERVICE, "Idempotency-Key": "tool-timeout"},
        )
        self.assertEqual(timeout.status_code, 504)
        self.assertEqual(timeout.json()["error"]["code"], "TOOL_TIMEOUT")

        missing = self.client.get("/api/v1/patients/lookup", params={"phone": "9990009999"}, headers=STAFF)
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
