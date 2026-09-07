from __future__ import annotations

import unittest
from unittest.mock import patch

from src.data.client import load_settings
from src.data.supabase_store import _patient_public_id, _scenario


class SupabaseClientTests(unittest.TestCase):
    def test_prefers_python_env_names(self) -> None:
        env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
            "NEXT_PUBLIC_SUPABASE_URL": "https://ignored.supabase.co",
            "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_ignored",
        }
        with patch("src.data.client._load_dotenv"), patch.dict("os.environ", env, clear=True):
            settings = load_settings()
        self.assertIsNotNone(settings)
        assert settings is not None
        self.assertEqual(settings.url, "https://example.supabase.co")
        self.assertEqual(settings.key, "sb_publishable_test")
        self.assertEqual(settings.key_kind, "publishable")

    def test_accepts_next_public_dashboard_names(self) -> None:
        env = {
            "NEXT_PUBLIC_SUPABASE_URL": "https://pjrhqtehfofgrhcdjtsh.supabase.co/",
            "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_demo",
        }
        with patch("src.data.client._load_dotenv"), patch.dict("os.environ", env, clear=True):
            settings = load_settings()
        self.assertIsNotNone(settings)
        assert settings is not None
        self.assertEqual(settings.url, "https://pjrhqtehfofgrhcdjtsh.supabase.co")
        self.assertEqual(settings.key_kind, "publishable")

    def test_secret_key_wins_over_publishable(self) -> None:
        env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
            "SUPABASE_SECRET_KEY": "sb_secret_test",
        }
        with patch("src.data.client._load_dotenv"), patch.dict("os.environ", env, clear=True):
            settings = load_settings()
        self.assertIsNotNone(settings)
        assert settings is not None
        self.assertEqual(settings.key, "sb_secret_test")
        self.assertEqual(settings.key_kind, "secret")

    def test_maps_existing_patient_rows(self) -> None:
        row = {
            "id": 1,
            "phone_number": "9990001111",
            "name": "TEST-PATIENT-001",
            "age": 34,
            "known_conditions": "SYN:Asthma",
            "known_allergies": "SYN:Penicillin",
        }
        self.assertEqual(_patient_public_id(row), "patient_demo_001")
        self.assertEqual(_scenario(row), "sufficient")
        missing = {"id": 4, "phone_number": None, "age": None, "known_conditions": None}
        self.assertEqual(_scenario(missing), "missing")


if __name__ == "__main__":
    unittest.main()
