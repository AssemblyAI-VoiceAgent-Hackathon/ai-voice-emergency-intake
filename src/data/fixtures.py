"""Deterministic synthetic patients and notes for development and demo.

Scenarios: sufficient, missing-information, conflicting-information, not-found.
Names use TEST-PATIENT-* and clinical text uses the SYN: prefix. No real
patient, caller, or identifiable personal data is included.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import re
from typing import Any, Optional

from .crypto import SYN_PREFIX, ensure_synthetic_text

NOT_FOUND_PHONE = "9990009999"
INTENTIONAL_ORPHANS = {999}
REQUIRED_SCENARIOS = {"sufficient", "missing", "conflicting"}
PHONE_PATTERN = re.compile(r"^999000\d{4}$")

FORBIDDEN_PATTERNS = (
    (r"(?i)password|secret|api[_-]?key|token|credential", "credential/sensitive data"),
    (r"\+91[- ]?[6-9]\d{9}", "real-format phone number"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN-like identifier"),
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email address"),
    (r"\bPAN[A-Z]{5}[0-9]{4}[A-Z]\b", "PAN card-like pattern"),
    (r"\b\d{12}\b", "Aadhaar-like identifier"),
)

# Integer `id` values are fixture keys only. Persistence public IDs are
# patient_demo_00N / note_demo_00N so Role 3 can map contract identifiers later.
PATIENTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "public_id": "patient_demo_001",
        "phone_number": "9990001111",
        "name": "TEST-PATIENT-001",
        "age": 34,
        "known_conditions": "SYN:Asthma",
        "known_allergies": "SYN:Penicillin",
        "scenario": "sufficient",
        "conflicting_fields": {},
        "created_at": "2026-09-02T10:00:00Z",
    },
    {
        "id": 2,
        "public_id": "patient_demo_002",
        "phone_number": "9990002222",
        "name": "TEST-PATIENT-002",
        "age": 29,
        "known_conditions": "SYN:Diabetes Type 1",
        "known_allergies": "SYN:None",
        "scenario": "sufficient",
        "conflicting_fields": {},
        "created_at": "2026-09-02T10:05:00Z",
    },
    {
        "id": 3,
        "public_id": "patient_demo_003",
        "phone_number": "9990003333",
        "name": "TEST-PATIENT-003",
        "age": 52,
        "known_conditions": "SYN:Hypertension, Coronary Artery Disease",
        "known_allergies": "SYN:Aspirin",
        "scenario": "sufficient",
        "conflicting_fields": {},
        "created_at": "2026-09-02T10:10:00Z",
    },
    {
        "id": 4,
        "public_id": "patient_demo_004",
        "phone_number": None,
        "name": "TEST-PATIENT-004",
        "age": None,
        "known_conditions": None,
        "known_allergies": "SYN:Peanuts",
        "scenario": "missing",
        "conflicting_fields": {},
        "created_at": "2026-09-02T10:15:00Z",
    },
    {
        "id": 6,
        "public_id": "patient_demo_006",
        "phone_number": "9990006666",
        "name": "TEST-PATIENT-006",
        "age": 61,
        "known_conditions": "SYN:Asthma",
        "known_allergies": "SYN:Penicillin, Aspirin",
        "scenario": "conflicting",
        "conflicting_fields": {
            "age": [61, 58, 64],
            "known_allergies": ["SYN:Penicillin, Aspirin", "SYN:None", "SYN:Sulfa"],
            "known_conditions": ["SYN:Asthma", "SYN:Asthma, COPD", "SYN:Asthma, Bronchitis"],
        },
        "created_at": "2026-09-02T10:20:00Z",
    },
    {
        "id": 7,
        "public_id": "patient_demo_007",
        "phone_number": "9990007777",
        "name": "TEST-PATIENT-007",
        "age": 30,
        "known_conditions": None,
        "known_allergies": None,
        "scenario": "missing",
        "conflicting_fields": {},
        "created_at": "2026-09-02T10:25:00Z",
    },
    {
        "id": 8,
        "public_id": "patient_demo_008",
        "phone_number": "9990008888",
        "name": "TEST-PATIENT-008",
        "age": None,
        "known_conditions": "SYN:Anemia",
        "known_allergies": None,
        "scenario": "missing",
        "conflicting_fields": {},
        "created_at": "2026-09-02T10:30:00Z",
    },
]

NOTES: list[dict[str, Any]] = [
    {
        "id": 1,
        "patient_id": 1,
        "note_date": "2026-07-14",
        "note_text": "SYN:Chest tightness, mild. Resolved after inhaler use.",
        "created_at": "2026-07-14T10:00:00Z",
    },
    {
        "id": 2,
        "patient_id": 1,
        "note_date": "2026-08-02",
        "note_text": "SYN:Follow-up: no recurrence, breathing normal.",
        "created_at": "2026-08-02T10:00:00Z",
    },
    {
        "id": 3,
        "patient_id": 2,
        "note_date": "2026-06-02",
        "note_text": "SYN:Dizziness, low blood sugar episode. Advised regular meal timing.",
        "created_at": "2026-06-02T10:00:00Z",
    },
    {
        "id": 4,
        "patient_id": 6,
        "note_date": "2026-06-15",
        "note_text": "SYN:Wheezing noted, inhaler prescribed.",
        "created_at": "2026-06-15T10:00:00Z",
    },
    {
        "id": 5,
        "patient_id": 6,
        "note_date": "2026-07-20",
        "note_text": "SYN:Conflicting source says no drug allergies.",
        "created_at": "2026-07-20T10:00:00Z",
    },
    {
        "id": 6,
        "patient_id": 999,
        "note_date": "2026-08-10",
        "note_text": "SYN:Orphan note for not-found scenario.",
        "created_at": "2026-08-10T10:00:00Z",
    },
    {
        "id": 7,
        "patient_id": 3,
        "note_date": "2026-05-20",
        "note_text": "SYN:Elevated BP reading during routine checkup, medication adjusted.",
        "created_at": "2026-05-20T10:00:00Z",
    },
    {
        "id": 8,
        "patient_id": 4,
        "note_date": "2026-06-02",
        "note_text": "SYN:Dizziness, low blood sugar episode.",
        "created_at": "2026-06-02T11:00:00Z",
    },
    {
        "id": 9,
        "patient_id": 6,
        "note_date": "2026-08-01",
        "note_text": "SYN:Patient reports COPD diagnosis from outside provider.",
        "created_at": "2026-08-01T10:00:00Z",
    },
]


@dataclass(frozen=True)
class Patient:
    id: int
    public_id: str
    phone_number: Optional[str]
    name: str
    age: Optional[int]
    known_conditions: Optional[str]
    known_allergies: Optional[str]
    scenario: str
    created_at: str
    conflicting_fields: dict[str, list[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.public_id.startswith("patient_demo_"):
            raise ValueError(f"Patient {self.id} public_id must start with patient_demo_")
        if not self.name.startswith("TEST-PATIENT-"):
            raise ValueError(f"Patient {self.id} name must start with TEST-PATIENT-")
        if self.age is not None and (self.age < 0 or self.age > 150):
            raise ValueError(f"Patient {self.id} has invalid age: {self.age}")
        if self.phone_number is not None and not PHONE_PATTERN.match(self.phone_number):
            raise ValueError(f"Patient {self.id} has invalid phone format: {self.phone_number}")
        if self.scenario not in REQUIRED_SCENARIOS:
            raise ValueError(f"Patient {self.id} has invalid scenario: {self.scenario}")
        if not self.created_at:
            raise ValueError(f"Patient {self.id} missing created_at timestamp")
        for field_name in ("known_conditions", "known_allergies"):
            value = getattr(self, field_name)
            if value is not None and not str(value).startswith(SYN_PREFIX):
                raise ValueError(f"Patient {self.id} {field_name} must start with {SYN_PREFIX}")


@dataclass(frozen=True)
class ClinicalNote:
    id: int
    patient_id: int
    note_date: str
    note_text: str
    created_at: str

    def __post_init__(self) -> None:
        normalized = ensure_synthetic_text(self.note_text) or ""
        if not normalized.startswith(SYN_PREFIX):
            raise ValueError(f"Note {self.id} must start with {SYN_PREFIX}")
        object.__setattr__(self, "note_text", normalized)
        try:
            datetime.strptime(self.note_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"Note {self.id} has invalid date format: {self.note_date}") from exc
        if not self.created_at:
            raise ValueError(f"Note {self.id} missing created_at timestamp")


class Store:
    """In-memory fixture index for Roles 2/5 and tests that do not need SQLite."""

    _instance: Optional["Store"] = None
    _initialized = False

    def __new__(cls) -> "Store":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not Store._initialized:
            self.patients: dict[int, Patient] = {}
            self.notes: dict[int, ClinicalNote] = {}
            self.notes_by_patient: dict[int, list[ClinicalNote]] = {}
            Store._initialized = True

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None
        cls._initialized = False


def load() -> None:
    store = Store()
    loaded_patients = [Patient(**row) for row in PATIENTS]
    store.patients = {item.id: item for item in loaded_patients}
    notes = [ClinicalNote(**row) for row in NOTES]
    store.notes = {note.id: note for note in notes}
    by_patient: dict[int, list[ClinicalNote]] = {}
    for note in notes:
        by_patient.setdefault(note.patient_id, []).append(note)
    for group in by_patient.values():
        group.sort(key=lambda item: item.note_date)
    store.notes_by_patient = by_patient


def reset() -> None:
    Store.reset_instance()
    load()


def get_patient_by_id(patient_id: int) -> Optional[Patient]:
    return Store().patients.get(patient_id)


def get_patient_by_phone(phone_number: Optional[str]) -> Optional[Patient]:
    if phone_number is None:
        return None
    return next((patient for patient in Store().patients.values() if patient.phone_number == phone_number), None)


def get_patient_by_public_id(public_id: str) -> Optional[Patient]:
    return next((patient for patient in Store().patients.values() if patient.public_id == public_id), None)


def get_notes_for_patient(patient_id: int) -> list[ClinicalNote]:
    return Store().notes_by_patient.get(patient_id, [])


def get_scenario_patient(scenario: str) -> Optional[Patient]:
    return next((patient for patient in Store().patients.values() if patient.scenario == scenario), None)


def get_all_patients_by_scenario(scenario: str) -> list[Patient]:
    return [patient for patient in Store().patients.values() if patient.scenario == scenario]


def get_conflicting_field_values(patient_id: int, field_name: str) -> Optional[list[Any]]:
    patient = get_patient_by_id(patient_id)
    if patient and patient.scenario == "conflicting":
        return patient.conflicting_fields.get(field_name)
    return None


def persistable_patients() -> list[Patient]:
    """Patients that can be inserted into SQLite (excludes orphan-only rows)."""
    load()
    return list(Store().patients.values())


def persistable_notes() -> list[ClinicalNote]:
    """Notes linked to a real fixture patient. Orphan notes stay in-memory only."""
    load()
    return [note for note in Store().notes.values() if note.patient_id not in INTENTIONAL_ORPHANS]


def synthetic_phone_allowlist() -> set[str]:
    load()
    phones = {patient.phone_number for patient in Store().patients.values() if patient.phone_number}
    phones.add(NOT_FOUND_PHONE)
    return phones


def fixture_payload() -> dict[str, Any]:
    load()
    store = Store()
    return {
        "patients": [asdict(patient) for patient in store.patients.values()],
        "notes": [asdict(note) for note in store.notes.values()],
        "not_found_phone": NOT_FOUND_PHONE,
        "metadata": {
            "total_patients": len(store.patients),
            "total_notes": len(store.notes),
            "scenarios": {
                scenario: len(get_all_patients_by_scenario(scenario)) for scenario in sorted(REQUIRED_SCENARIOS)
            },
        },
    }


def export_fixtures_to_json(filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(fixture_payload(), handle, indent=2)
        handle.write("\n")


def validate() -> list[str]:
    load()
    errors: list[str] = []
    store = Store()

    if len(store.patients) != len({patient.id for patient in store.patients.values()}):
        errors.append("Duplicate patient IDs detected")
    if len(store.notes) != len({note.id for note in store.notes.values()}):
        errors.append("Duplicate note IDs detected")
    if len({patient.public_id for patient in store.patients.values()}) != len(store.patients):
        errors.append("Duplicate patient public_id values detected")

    for note in store.notes.values():
        if note.patient_id not in store.patients and note.patient_id not in INTENTIONAL_ORPHANS:
            errors.append(f"Note {note.id} references unknown patient {note.patient_id}")

    present = {patient.scenario for patient in store.patients.values()}
    missing_scenarios = REQUIRED_SCENARIOS - present
    if missing_scenarios:
        errors.append(f"Missing required scenarios: {sorted(missing_scenarios)}")

    sufficient = get_all_patients_by_scenario("sufficient")
    if len(sufficient) < 3:
        errors.append("Need at least 3 sufficient scenario patients")
    for patient in sufficient:
        if not all(
            [
                patient.phone_number,
                patient.name,
                patient.age is not None,
                patient.known_conditions,
                patient.known_allergies,
            ]
        ):
            errors.append(f"Sufficient patient {patient.id} has missing required fields")

    missing = get_all_patients_by_scenario("missing")
    if len(missing) < 3:
        errors.append("Need at least 3 missing scenario patients with different missing fields")
    for patient in missing:
        if all(
            [
                patient.phone_number is not None,
                patient.age is not None,
                patient.known_conditions is not None,
                patient.known_allergies is not None,
            ]
        ):
            errors.append(f"Missing patient {patient.id} has no missing fields")
    if not any(get_notes_for_patient(patient.id) == [] for patient in missing):
        errors.append("At least one missing patient should have no notes")
    if not any(patient.phone_number is None for patient in missing):
        errors.append("At least one missing patient should have null phone")

    conflicting = get_all_patients_by_scenario("conflicting")
    if not conflicting:
        errors.append("Need at least 1 conflicting scenario patient")
    for patient in conflicting:
        if len(patient.conflicting_fields) < 2:
            errors.append(f"Conflicting patient {patient.id} needs at least 2 conflicting fields")
        for field_name, values in patient.conflicting_fields.items():
            if len(values) < 2:
                errors.append(f"Conflicting patient {patient.id} field '{field_name}' needs at least 2 values")
            if len(set(str(item) for item in values)) != len(values):
                errors.append(f"Conflicting patient {patient.id} field '{field_name}' has duplicate values")

    if get_patient_by_phone(NOT_FOUND_PHONE) is not None:
        errors.append("Not-found phone unexpectedly resolved to a patient")
    if get_patient_by_id(999) is not None:
        errors.append("Orphan patient 999 unexpectedly exists in patients store")
    if len(get_notes_for_patient(999)) != 1:
        errors.append(f"Expected exactly 1 orphan note for patient 999, found {len(get_notes_for_patient(999))}")

    blob = json.dumps(fixture_payload())
    for pattern, reason in FORBIDDEN_PATTERNS:
        if re.search(pattern, blob):
            errors.append(f"SAFETY VIOLATION - {reason} found in fixtures")

    phones = [patient.phone_number for patient in store.patients.values() if patient.phone_number]
    if len(phones) != len(set(phones)):
        errors.append("Duplicate phone numbers detected across patients")

    created_times = [patient.created_at for patient in store.patients.values()]
    if len(created_times) != len(set(created_times)):
        errors.append("Patient created_at timestamps are not unique/staggered")

    return errors
