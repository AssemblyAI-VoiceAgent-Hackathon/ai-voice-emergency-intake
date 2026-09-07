"""JSON Schema validation for Role 2 and Role 5 payloads."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import ApiError

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"


@lru_cache(maxsize=8)
def _validator(name: str) -> Draft202012Validator:
    with (CONTRACTS / name).open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _field_errors(errors: list) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for err in sorted(errors, key=lambda item: list(item.path)):
        path = "/" + "/".join(str(part) for part in err.path) if err.path else "/"
        out.append({"path": path, "message": "Failed schema validation."})
    return out[:20]


def validate_structured_case(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiError(400, "MALFORMED_JSON", "The request body is not valid JSON.")
    errors = list(_validator("structured-case.schema.json").iter_errors(payload))
    if errors:
        raise ApiError(
            422,
            "SCHEMA_VALIDATION_FAILED",
            "The structured case is not valid.",
            field_errors=_field_errors(errors),
        )
    return payload


def validate_staff_review(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiError(400, "MALFORMED_JSON", "The request body is not valid JSON.")
    errors = list(_validator("staff-review.schema.json").iter_errors(payload))
    if errors:
        raise ApiError(
            422,
            "SCHEMA_VALIDATION_FAILED",
            "The staff review is not valid.",
            field_errors=_field_errors(errors),
        )
    return payload


LOOKUP_TOOL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "phone": {"type": "string", "minLength": 8, "maxLength": 32},
        "patientPublicId": {"type": "string", "minLength": 1, "maxLength": 64},
        "simulate": {"type": "string", "enum": ["timeout", "failure"]},
    },
    "anyOf": [{"required": ["phone"]}, {"required": ["patientPublicId"]}, {"required": ["simulate"]}],
}


def validate_tool_arguments(tool: str, arguments: Any) -> dict[str, Any]:
    if tool != "lookup_patient":
        raise ApiError(422, "UNKNOWN_TOOL", "The requested tool is not available.")
    if not isinstance(arguments, dict):
        raise ApiError(422, "INVALID_TOOL_ARGUMENTS", "Tool arguments must be an object.")
    validator = Draft202012Validator(LOOKUP_TOOL_SCHEMA)
    errors = list(validator.iter_errors(arguments))
    if errors:
        raise ApiError(
            422,
            "INVALID_TOOL_ARGUMENTS",
            "Tool arguments failed schema validation.",
            field_errors=_field_errors(errors),
        )
    return arguments
