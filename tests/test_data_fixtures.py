from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.data import (
    NOT_FOUND_PHONE,
    get_all_patients_by_scenario,
    get_notes_for_patient,
    get_patient_by_id,
    get_patient_by_phone,
    load_fixtures,
    reset_fixtures,
    validate_fixtures,
)
from src.data.fixtures import fixture_payload

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "src" / "data" / "synthetic" / "records.json"


class FixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fixtures()

    def test_validate_passes(self) -> None:
        self.assertEqual(validate_fixtures(), [])

    def test_scenarios_and_not_found(self) -> None:
        load_fixtures()
        self.assertGreaterEqual(len(get_all_patients_by_scenario("sufficient")), 3)
        self.assertGreaterEqual(len(get_all_patients_by_scenario("missing")), 3)
        self.assertGreaterEqual(len(get_all_patients_by_scenario("conflicting")), 1)
        self.assertIsNone(get_patient_by_phone(NOT_FOUND_PHONE))
        self.assertIsNone(get_patient_by_id(999))
        self.assertEqual(len(get_notes_for_patient(999)), 1)

    def test_deterministic_ids(self) -> None:
        load_fixtures()
        first = get_patient_by_phone("9990001111")
        reset_fixtures()
        second = get_patient_by_phone("9990001111")
        self.assertIsNotNone(first)
        self.assertEqual(first.public_id, "patient_demo_001")
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.name, "TEST-PATIENT-001")

    def test_exported_json_matches_source(self) -> None:
        with RECORDS.open(encoding="utf-8") as handle:
            on_disk = json.load(handle)
        self.assertEqual(on_disk, fixture_payload())

    def test_no_real_looking_personal_names(self) -> None:
        blob = json.dumps(fixture_payload())
        for banned in ("Rahul", "Aisha", "Sameer", "Priya", "Vikram"):
            self.assertNotIn(banned, blob)


if __name__ == "__main__":
    unittest.main()
