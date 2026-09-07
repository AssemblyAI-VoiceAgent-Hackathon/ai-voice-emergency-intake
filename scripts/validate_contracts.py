"""Validate the repository's synthetic examples against their JSON Schemas."""

from json import load
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
PAIRS = (
    (CONTRACTS / "intake-transcript.schema.json", CONTRACTS / "examples" / "intake-transcript.example.json"),
    (CONTRACTS / "structured-case.schema.json", CONTRACTS / "examples" / "structured-case.example.json"),
    (
        CONTRACTS / "structured-case.schema.json",
        CONTRACTS / "examples" / "structured-case.sufficient.example.json",
    ),
    (
        CONTRACTS / "structured-case.schema.json",
        CONTRACTS / "examples" / "structured-case.conflicting.example.json",
    ),
    (CONTRACTS / "staff-review.schema.json", CONTRACTS / "examples" / "staff-review.example.json"),
)


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as file:
        return load(file)


def main() -> None:
    failed = False
    for schema_path, example_path in PAIRS:
        schema = read_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(read_json(example_path)), key=lambda error: list(error.path))
        if errors:
            failed = True
            print(f"FAIL {example_path.relative_to(ROOT)}")
            for error in errors:
                location = "/".join(str(part) for part in error.path) or "<root>"
                print(f"  {location}: {error.message}")
        else:
            print(f"PASS {example_path.relative_to(ROOT)}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

