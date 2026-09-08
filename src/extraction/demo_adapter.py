"""Deterministic Role 2 adapter used when no external model is configured.

Copies only facts from final, non-agent turns. Negated statements are not
treated as present. Missing items become information gaps for staff, never a
triage decision or diagnosis.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

_WORD_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_GREETING_RE = re.compile(
    r"^(hey|hi|hello|yeah|yes|yo|ok|okay|um|uh)[\s.!?]*$",
    re.IGNORECASE,
)
_AGE_RE = re.compile(
    r"(?:i(?:'m| am)|age is(?: like)?|i am)\s*(\d{1,3})\b|\b(\d{1,3})\s*(?:years?\s*old|yo)\b",
    re.IGNORECASE,
)
_SEVERITY_RANGE_RE = re.compile(
    r"\b(?:(\d{1,2})|(" + "|".join(_WORD_NUMBERS) + r"))\s*(?:to|-)\s*(?:(\d{1,2})|("
    + "|".join(_WORD_NUMBERS)
    + r"))\b",
    re.IGNORECASE,
)
_SEVERITY_SCALE_RE = re.compile(
    r"\b(?:(\d{1,2})|(" + "|".join(_WORD_NUMBERS) + r"))\s*(?:out of|/)\s*10\b",
    re.IGNORECASE,
)
_ONSET_RE = re.compile(
    r"\b(this morning|this afternoon|this evening|last night|yesterday|"
    r"for about [^.,;]{2,40}|about [^.,;]{2,20} ago|since [^.,;]{2,40}|"
    r"started? in the morning|started? last night|"
    r"\d+\s*(?:minutes?|hours?|days?)\s*ago)\b",
    re.IGNORECASE,
)
_NEGATION_RE = re.compile(
    r"\b(no|not|never|without|don't|dont|didn't|didnt|doesn't|doesnt|"
    r"isn't|isnt|aren't|arent|cannot|can't|cant|denied|deny)\b",
    re.IGNORECASE,
)

_LOCATIONS = (
    ("left arm", "left arm"),
    ("right arm", "right arm"),
    ("left shoulder", "left shoulder"),
    ("right shoulder", "right shoulder"),
    ("shoulder", "shoulder"),
    ("central chest", "central chest"),
    ("chest", "chest"),
    ("head", "head"),
    ("abdomen", "abdomen"),
    ("stomach", "abdomen"),
    ("back", "back"),
    ("left leg", "left leg"),
    ("right leg", "right leg"),
    ("left ankle", "left ankle"),
    ("right ankle", "right ankle"),
    ("ankle", "ankle"),
)

_SYMPTOM_HINTS = (
    ("chest pain", "chest pain", "chest", ("chest pain", "chest discomfort", "chest tightness", "chest pressure", "chest hurts")),
    ("shortness of breath", "shortness of breath", None, ("short of breath", "shortness of breath", "trouble breathing", "can't breathe", "cannot breathe", "difficulty breathing")),
    ("left arm pain", "left arm pain", "left arm", ("left arm", "arm shoulder")),
    ("arm pain", "arm pain", "arm", ("arm pain", "pain in my arm", "pain in the arm")),
    ("fainting", "fainting", None, ("fainting", "passed out", "feel faint", "feeling of fainting")),
    ("swelling", "swelling", None, ("swollen", "swelling")),
    ("bleeding", "bleeding", None, ("bleeding", "uncontrolled bleeding")),
)

_SAFETY_HINTS = (
    ("chest_pain", "Chest pain reported", ("chest pain", "chest discomfort", "chest pressure", "chest tightness", "chest hurts")),
    ("respiratory_distress", "Breathing difficulty reported", ("short of breath", "trouble breathing", "not breathing", "can't breathe", "cannot breathe")),
    ("uncontrolled_bleeding", "Bleeding reported", ("uncontrolled bleeding", "severe bleeding")),
    ("unresponsive", "Unresponsive patient reported", ("unresponsive", "not responding", "unconscious")),
    ("syncope", "Fainting reported", ("fainting", "passed out", "collapsed")),
)

_CONDITIONS = (
    ("hypertension", ("high blood pressure", "hypertension")),
    ("diabetes", ("diabetes", "diabetic")),
    ("asthma", ("asthma",)),
    ("heart disease", ("heart disease", "heart condition", "coronary")),
)


def _to_int_word(raw: str | None) -> int | None:
    if raw is None:
        return None
    key = raw.lower()
    if key in _WORD_NUMBERS:
        return _WORD_NUMBERS[key]
    if raw.isdigit():
        value = int(raw)
        return value if 0 <= value <= 10 else None
    return None


def _evidence_turns(intake: Mapping[str, Any]) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for turn in intake.get("turns") or []:
        if not isinstance(turn, Mapping):
            continue
        if turn.get("final") is True and turn.get("speaker") != "agent":
            turns.append(dict(turn))
    return turns


def _joined_text(turns: list[dict[str, Any]]) -> str:
    return " ".join(str(turn.get("text") or "") for turn in turns)


def _is_negated(text: str, index: int) -> bool:
    window = text[max(0, index - 32) : index]
    return bool(_NEGATION_RE.search(window))


def _mention_turns(turns: list[dict[str, Any]], needles: tuple[str, ...], *, allow_negated: bool = False) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for turn in turns:
        lower = str(turn.get("text") or "").lower()
        for needle in needles:
            index = lower.find(needle)
            if index < 0:
                continue
            if not allow_negated and _is_negated(lower, index):
                continue
            matched.append(turn)
            break
    return matched


def _denied_turns(turns: list[dict[str, Any]], needles: tuple[str, ...]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for turn in turns:
        lower = str(turn.get("text") or "").lower()
        for needle in needles:
            index = lower.find(needle)
            if index >= 0 and _is_negated(lower, index):
                matched.append(turn)
                break
    return matched


def _onset(text: str) -> str | None:
    match = _ONSET_RE.search(text)
    if not match:
        return None
    return match.group(1).strip(" .")


def _severity(text: str) -> int | None:
    ranged = _SEVERITY_RANGE_RE.search(text)
    if ranged:
        values = [_to_int_word(part) for part in ranged.groups()]
        numbers = [item for item in values if item is not None]
        if numbers:
            return max(numbers)
    scale = _SEVERITY_SCALE_RE.search(text)
    if scale:
        return _to_int_word(scale.group(1) or scale.group(2))
    return None


def _location(text: str) -> str | None:
    lower = text.lower()
    for needle, label in _LOCATIONS:
        index = lower.find(needle)
        if index >= 0 and not _is_negated(lower, index):
            return label
    return None


def _informants(turns: list[dict[str, Any]]) -> list[str]:
    order = ["patient", "caregiver", "staff", "unknown"]
    blob = _joined_text(turns).lower()
    found = {turn.get("speaker") for turn in turns if turn.get("speaker") in order}
    if "calling for" in blob or "someone else" in blob or "my child" in blob or "my wife" in blob or "my husband" in blob:
        found.add("caregiver")
    return [name for name in order if name in found] or ["unknown"]


def _chief_turn(turns: list[dict[str, Any]]) -> dict[str, Any] | None:
    for turn in turns:
        text = str(turn.get("text") or "").strip()
        if text and not _GREETING_RE.match(text):
            return turn
    return turns[0] if turns else None


def _history_status(turns: list[dict[str, Any]], topic: str, present_needles: tuple[str, ...]) -> tuple[str, list[str]] | None:
    unknown_tokens = (
        "unknown",
        "not sure",
        "don't know",
        "dont know",
        "cannot remember",
        "can't remember",
        "dont remember",
        "can't recall",
    )
    unknown = [
        turn
        for turn in turns
        if topic in str(turn.get("text") or "").lower()
        and any(token in str(turn.get("text") or "").lower() for token in unknown_tokens)
    ]
    if unknown:
        return "unknown", []
    denied = _denied_turns(turns, present_needles)
    mentioned = _mention_turns(turns, present_needles)
    if denied and not mentioned:
        return "denied", [turn["turnId"] for turn in denied]
    if mentioned:
        return "reported", [turn["turnId"] for turn in mentioned]
    return None


def generate_structured_case(intake: Mapping[str, Any]) -> dict[str, Any]:
    """Return a schema-shaped StructuredCase. Engine injects extractionMetadata."""

    evidence = _evidence_turns(intake)
    blob = _joined_text(evidence)
    chief = _chief_turn(evidence)
    first_ref = chief["turnId"] if chief else None
    first_text = str(chief["text"]) if chief else None
    onset = _onset(blob) if blob else None
    severity = _severity(blob) if blob else None
    location = _location(blob) if blob else None

    symptoms: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for _key, label, default_location, needles in _SYMPTOM_HINTS:
        matching = _mention_turns(evidence, needles)
        if not matching:
            continue
        if label in seen_names:
            continue
        seen_names.add(label)
        local_text = " ".join(str(turn.get("text") or "") for turn in matching)
        symptoms.append(
            {
                "name": label,
                "present": True,
                "onsetText": _onset(local_text) or onset,
                "severity0To10": _severity(local_text) or severity,
                "location": _location(local_text) or default_location or location,
                "notes": None,
                "sourceRefs": [turn["turnId"] for turn in matching],
            }
        )

    if first_text and "pain" in first_text.lower() and not any("pain" in item["name"] for item in symptoms):
        symptoms.insert(
            0,
            {
                "name": f"{location} pain" if location else "pain",
                "present": True,
                "onsetText": onset,
                "severity0To10": severity,
                "location": location,
                "notes": None,
                "sourceRefs": [first_ref] if first_ref else [],
            },
        )

    allergies: list[dict[str, Any]] = []
    allergy_status = _history_status(evidence, "allerg", ("allerg", "allergy", "allergies"))
    if allergy_status:
        status, refs = allergy_status
        allergies.append(
            {
                "name": "known allergies",
                "status": status,
                "details": None,
                "sourceRefs": refs,
            }
        )

    medications: list[dict[str, Any]] = []
    med_status = _history_status(evidence, "medic", ("medication", "medications", "medicine", "medicines", "pills"))
    if med_status:
        status, refs = med_status
        medications.append(
            {
                "name": "current medications",
                "status": status,
                "details": None,
                "sourceRefs": refs,
            }
        )

    conditions: list[dict[str, Any]] = []
    for name, needles in _CONDITIONS:
        matching = _mention_turns(evidence, needles)
        denied = _denied_turns(evidence, needles)
        if matching:
            conditions.append(
                {
                    "name": name,
                    "status": "reported",
                    "details": None,
                    "sourceRefs": [turn["turnId"] for turn in matching],
                }
            )
        elif denied:
            conditions.append(
                {
                    "name": name,
                    "status": "denied",
                    "details": None,
                    "sourceRefs": [turn["turnId"] for turn in denied],
                }
            )

    age = None
    age_match = _AGE_RE.search(blob)
    if age_match:
        parsed = int(next(part for part in age_match.groups() if part))
        if 0 <= parsed <= 130:
            age = parsed

    sex = None
    lower = blob.lower()
    if re.search(r"\b(female|woman|girl)\b", lower):
        sex = "female"
    elif re.search(r"\b(male|man|boy)\b", lower):
        sex = "male"
    elif "intersex" in lower:
        sex = "intersex"

    safety: list[dict[str, Any]] = []
    for code, label, needles in _SAFETY_HINTS:
        matching = _mention_turns(evidence, needles)
        if matching:
            safety.append(
                {
                    "code": code,
                    "label": label,
                    "status": "present",
                    "evidenceSourceRefs": [turn["turnId"] for turn in matching],
                }
            )

    observations: list[dict[str, Any]] = []
    for record in intake.get("observations") or []:
        if not isinstance(record, Mapping) or not record.get("sourceRef"):
            continue
        observations.append(
            {
                "name": record.get("name") or "observation",
                "value": record.get("value"),
                "unit": record.get("unit"),
                "origin": "reported",
                "observedAt": record.get("recordedAt"),
                "sourceRefs": [record["sourceRef"]],
            }
        )
    for record in intake.get("verifiedRecords") or []:
        if not isinstance(record, Mapping) or not record.get("sourceRef"):
            continue
        observations.append(
            {
                "name": record.get("name") or "verified_record",
                "value": record.get("value"),
                "unit": record.get("unit"),
                "origin": "verified_record",
                "observedAt": record.get("recordedAt"),
                "sourceRefs": [record["sourceRef"]],
            }
        )

    gaps: list[dict[str, Any]] = []
    if first_text is None:
        gaps.append({"fieldPath": "/chiefComplaint/text", "question": "What is the main problem right now?", "priority": "required"})
    if onset is None:
        gaps.append({"fieldPath": "/chiefComplaint/onsetText", "question": "When did this start?", "priority": "required"})
    if age is None:
        gaps.append({"fieldPath": "/subject/ageYears", "question": "What is the patient's approximate age?", "priority": "required"})
    if sex is None:
        gaps.append({"fieldPath": "/subject/sexAtBirth", "question": "Is the patient male, female, or unknown?", "priority": "recommended"})
    if not allergies:
        gaps.append({"fieldPath": "/history/allergies", "question": "Does the patient have any allergies?", "priority": "required"})
    if not medications:
        gaps.append({"fieldPath": "/history/medications", "question": "What medicines does the patient take?", "priority": "required"})
    if symptoms and all(item.get("severity0To10") is None for item in symptoms) and any("pain" in item["name"] for item in symptoms):
        gaps.append({"fieldPath": "/symptoms/0/severity0To10", "question": "How bad is the pain from 0 to 10?", "priority": "recommended"})

    provenance: list[dict[str, Any]] = []
    if first_ref and first_text:
        provenance.append(
            {
                "fieldPath": "/chiefComplaint/text",
                "sourceRefs": [first_ref],
                "confidence": "high",
                "verificationStatus": "reported",
            }
        )
    if allergies and allergies[0]["sourceRefs"]:
        provenance.append(
            {
                "fieldPath": "/history/allergies/0/status",
                "sourceRefs": allergies[0]["sourceRefs"],
                "confidence": "high",
                "verificationStatus": "reported",
            }
        )

    status = "needs_information" if any(gap["priority"] == "required" for gap in gaps) else (
        "needs_information" if gaps else "ready_for_review"
    )
    one_line = first_text
    if one_line and len(one_line) > 160:
        one_line = one_line[:157] + "..."

    return {
        "schemaVersion": intake.get("schemaVersion"),
        "caseId": intake.get("caseId"),
        "sessionId": intake.get("sessionId"),
        "caseVersion": intake.get("caseVersion"),
        "status": status,
        "capturedAt": intake.get("capturedAt"),
        "language": intake.get("language"),
        "subject": {
            "patientReference": None,
            "ageYears": age,
            "sexAtBirth": sex,
        },
        "informants": _informants(evidence),
        "chiefComplaint": {
            "text": first_text,
            "onsetText": onset,
            "sourceRefs": [first_ref] if first_ref else [],
        },
        "symptoms": symptoms,
        "observations": observations,
        "history": {
            "conditions": conditions,
            "medications": medications,
            "allergies": allergies,
        },
        "summary": {
            "oneLine": one_line,
            "narrative": blob or None,
        },
        "safetySignals": safety,
        "informationGaps": gaps,
        "conflicts": [],
        "provenance": provenance,
    }


def demo_generate(prompt: str) -> dict[str, Any]:
    """ModelAdapter: recover SOURCE_DATA from the Role 2 prompt envelope."""

    marker = "SOURCE_DATA_BEGIN"
    end = "SOURCE_DATA_END"
    start = prompt.find(marker)
    stop = prompt.find(end)
    if start < 0 or stop < 0 or stop <= start:
        raise ValueError("prompt missing source data")

    raw = prompt[start + len(marker) : stop].strip()
    intake = json.loads(raw)
    return generate_structured_case(intake)
