"""Role 5 review-workflow checks against the frozen staff-review contract."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from src.backend.edits import apply_edits

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts" / "examples"
SCHEMA = ROOT / "contracts" / "staff-review.schema.json"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class DashboardWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(_load(SCHEMA), format_checker=FormatChecker())
        self.case = _load(EXAMPLES / "structured-case.example.json")
        self.conflicting = _load(EXAMPLES / "structured-case.conflicting.example.json")

    def _assert_valid(self, payload: dict) -> None:
        errors = sorted(self.validator.iter_errors(payload), key=lambda err: list(err.path))
        self.assertFalse(errors, [err.message for err in errors])

    def test_save_draft_request_info_and_approve_payloads_validate(self) -> None:
        draft = {
            "schemaVersion": "1.0.0",
            "caseId": "case_demo_001",
            "baseCaseVersion": 3,
            "idempotencyKey": "review-demo-draft-01",
            "action": "save_draft",
            "edits": [],
            "informationRequest": None,
            "finalTriage": None,
            "comment": None,
        }
        more = {
            "schemaVersion": "1.0.0",
            "caseId": "case_demo_conflicting",
            "baseCaseVersion": 2,
            "idempotencyKey": "review-demo-info-01",
            "action": "request_more_information",
            "edits": [],
            "informationRequest": {"questions": ["Please confirm allergy history."]},
            "finalTriage": None,
            "comment": None,
        }
        approve = {
            "schemaVersion": "1.0.0",
            "caseId": "case_demo_001",
            "baseCaseVersion": 3,
            "idempotencyKey": "review-demo-approve-01",
            "action": "approve",
            "edits": [
                {
                    "op": "replace",
                    "path": "/history/allergies",
                    "value": [
                        {
                            "name": "penicillin",
                            "status": "reported",
                            "details": "Patient reports a rash",
                            "sourceRefs": ["staff_review_01"],
                        }
                    ],
                    "reason": "Confirmed directly by staff during review",
                }
            ],
            "informationRequest": None,
            "finalTriage": {
                "code": "ESI-2",
                "label": "Urgent",
                "rationale": "Human-selected after review",
            },
            "comment": "Synthetic workflow test",
        }
        self._assert_valid(draft)
        self._assert_valid(more)
        self._assert_valid(approve)

    def test_staff_edits_survive_later_ai_overlay(self) -> None:
        edits = [
            {
                "op": "replace",
                "path": "/chiefComplaint/text",
                "value": "Staff-corrected chest pain",
                "reason": "Confirmed on arrival",
            }
        ]
        later = deepcopy(self.case)
        later["chiefComplaint"]["text"] = "AI restated chest discomfort"
        later["caseVersion"] = 4
        merged = apply_edits(later, edits)
        self.assertEqual(merged["chiefComplaint"]["text"], "Staff-corrected chest pain")
        self.assertEqual(merged["caseVersion"], 4)

    def test_required_gaps_block_approval_until_resolved(self) -> None:
        required = [
            gap
            for gap in self.conflicting.get("informationGaps", [])
            if gap.get("priority") == "required"
        ]
        self.assertTrue(required)
        pending_paths = {gap["fieldPath"] for gap in required}
        self.assertTrue(pending_paths)
        resolved = pending_paths
        still_open = [
            gap for gap in required if gap["fieldPath"] not in resolved
        ]
        self.assertEqual(still_open, [])

    def test_conflict_envelope_keeps_latest_version(self) -> None:
        body = {
            "error": {
                "code": "CASE_VERSION_CONFLICT",
                "message": "The submitted case version is stale.",
                "latestCaseVersion": 7,
            }
        }
        self.assertEqual(body["error"]["latestCaseVersion"], 7)
        self.assertEqual(body["error"]["code"], "CASE_VERSION_CONFLICT")
