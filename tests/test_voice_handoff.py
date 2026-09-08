from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("ARIA_VOICE_DEMO", "1")
os.environ.setdefault("ARIA_BACKEND", "sqlite")

from src.extraction import extract_structured_case
from src.extraction.demo_adapter import demo_generate, generate_structured_case
from src.voice.handoff import build_intake_transcript, handoff_transcript
from src.voice.turns import sanitize_turns


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "contracts" / "examples" / "intake-transcript.example.json"


class TurnSanitizationTests(unittest.TestCase):
    def test_drops_incomplete_and_aliases_speaker(self) -> None:
        cleaned = sanitize_turns(
            [
                {"speaker": "you", "text": "  Hello there  ", "final": True},
                {"speaker": "patient"},
                {"speaker": "not-a-role", "text": "Still a real utterance", "final": True},
                "ignore me",
            ]
        )
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["speaker"], "patient")
        self.assertEqual(cleaned[0]["text"], "Hello there")
        self.assertEqual(cleaned[0]["turnId"], "turn_1")
        self.assertTrue(cleaned[0]["final"])
        self.assertEqual(cleaned[1]["speaker"], "unknown")


class HandoffTests(unittest.TestCase):
    def test_example_transcript_extracts_and_ingests(self) -> None:
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        accepted: dict = {}

        def fake_ingest(payload: dict) -> dict:
            accepted.update(payload)
            return {
                "httpStatus": 202,
                "body": {
                    "status": "accepted",
                    "caseId": payload["caseId"],
                    "caseVersion": payload["caseVersion"],
                    "eventType": "case.snapshot",
                },
            }

        result = handoff_transcript(example, ingest=fake_ingest)
        self.assertEqual(result["extraction"]["status"], "success", result["extraction"])
        self.assertEqual(accepted["caseId"], example["caseId"])
        self.assertEqual(accepted["sessionId"], example["sessionId"])
        self.assertNotIn("finalTriage", accepted)
        self.assertNotIn("diagnosis", accepted)
        self.assertEqual(result["ingest"]["httpStatus"], 202)

    def test_malformed_turns_are_repaired_before_extraction(self) -> None:
        intake = build_intake_transcript(
            [
                {"speaker": "you", "text": "My chest hurts and I am short of breath."},
                {"speaker": "agent", "text": "Okay, I have that."},
            ],
            case_id="case_demo_voice",
            session_id="session_demo_voice",
        )
        result = extract_structured_case(intake, generate=demo_generate, model_name="role2-demo-adapter")
        self.assertTrue(result.ok, result.to_dict())
        payload = result.payload or {}
        self.assertEqual(payload["caseId"], "case_demo_voice")
        self.assertEqual(payload["status"], "needs_information")
        self.assertTrue(any(signal["code"] == "chest_pain" for signal in payload["safetySignals"]))

    def test_empty_transcript_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_intake_transcript([{"speaker": "patient", "text": "   "}])


class VoiceAppTests(unittest.TestCase):
    def test_health_and_handoff_route(self) -> None:
        import sys

        voice_root = ROOT / "src" / "voice"
        sys.path.insert(0, str(voice_root))
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["role"], "1")
            self.assertEqual(health.json()["mode"], "demo")

            empty = client.post("/api/voice/handoff", json={"turns": [{"speaker": "patient", "text": ""}]})
            self.assertEqual(empty.status_code, 422)

            accepted: dict = {}

            def fake_ingest(payload: dict) -> dict:
                accepted.update(payload)
                return {"httpStatus": 202, "body": {"status": "accepted", "caseId": payload["caseId"]}}

            from src.voice import handoff as handoff_mod

            original = handoff_mod.ingest_structured_case
            handoff_mod.ingest_structured_case = fake_ingest
            try:
                response = client.post(
                    "/api/voice/handoff",
                    json={
                        "caseId": "case_voice_app",
                        "sessionId": "session_voice_app",
                        "turns": [{"speaker": "you", "text": "Hello there", "final": True}],
                    },
                )
            finally:
                handoff_mod.ingest_structured_case = original
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(response.json()["intake"]["turns"][0]["speaker"], "patient")
            self.assertEqual(accepted["caseId"], "case_voice_app")


class DemoAdapterTests(unittest.TestCase):
    def test_does_not_invent_clinical_decisions(self) -> None:
        intake = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        candidate = generate_structured_case(intake)
        self.assertNotIn("finalTriage", candidate)
        self.assertNotIn("diagnosis", candidate)
        self.assertEqual(candidate["caseId"], intake["caseId"])
        self.assertGreaterEqual(len(candidate["chiefComplaint"]["sourceRefs"]), 1)
        self.assertFalse(any(item["name"] == "bleeding" for item in candidate["symptoms"]))
        self.assertEqual(candidate["history"]["conditions"][0]["name"], "hypertension")
        self.assertEqual(candidate["history"]["allergies"][0]["status"], "unknown")

    def test_maps_confirmed_answers_and_ignores_negation(self) -> None:
        intake = build_intake_transcript(
            [
                {"speaker": "patient", "text": "Hey."},
                {"speaker": "patient", "text": "I think I have a pain in my left arm."},
                {"speaker": "patient", "text": "It started in the morning."},
                {"speaker": "patient", "text": "I take no medications."},
                {"speaker": "patient", "text": "I have no allergies."},
                {"speaker": "patient", "text": "5 to 6. It's like arm shoulder side."},
                {"speaker": "patient", "text": "My age is like 23, male."},
                {
                    "speaker": "patient",
                    "text": "No, I don't have any chest pain or trouble breathing or any feeling of fainting. Just pain in my arm.",
                },
            ]
        )
        candidate = generate_structured_case(intake)
        self.assertEqual(candidate["subject"]["ageYears"], 23)
        self.assertEqual(candidate["subject"]["sexAtBirth"], "male")
        self.assertIn("morning", (candidate["chiefComplaint"]["onsetText"] or "").lower())
        self.assertFalse(any(item["name"] == "chest pain" for item in candidate["symptoms"]))
        self.assertTrue(any("arm" in item["name"] for item in candidate["symptoms"]))
        self.assertFalse(any(signal["code"] == "chest_pain" for signal in candidate["safetySignals"]))
        self.assertEqual(candidate["history"]["allergies"][0]["status"], "denied")
        self.assertEqual(candidate["history"]["medications"][0]["status"], "denied")
        self.assertNotIn("finalTriage", candidate)


if __name__ == "__main__":
    unittest.main()
