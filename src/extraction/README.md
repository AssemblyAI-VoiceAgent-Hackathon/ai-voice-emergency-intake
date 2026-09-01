# Role 2 extraction

`extract_structured_case` is the provider-neutral boundary between transcript
sources and the backend's `StructuredCase` payload.

The caller supplies a `generate(prompt)` adapter for the team's chosen AI
provider. The engine validates the intake before calling the provider, injects
engine-owned prompt/model metadata, and returns a payload only after all of
these checks pass:

- the output matches `contracts/structured-case.schema.json`;
- case/session/version metadata is unchanged;
- every source reference exists and is final, non-agent evidence;
- no diagnosis, treatment plan, or final triage field is present; and
- a case with gaps or unresolved conflicts is not labelled ready for review.

Failures contain stable codes and JSON Pointer paths but no transcript or model
content. Role 3 can map `ExtractionResult.to_dict()` into its API error envelope.

Minimal integration:

```python
from src.extraction import extract_structured_case

result = extract_structured_case(
    synthetic_intake,
    generate=provider_adapter,
    model_name="configured-by-role-3",
)

if result.ok:
    submit_to_backend(result.payload)
else:
    handle_failure(result.to_dict())
```

The repository does not include provider credentials or network calls. Use
synthetic data only during development and keep provider secrets in the backend
environment.
