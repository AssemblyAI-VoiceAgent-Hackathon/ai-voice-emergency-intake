"""FastAPI application for Role 3 ingestion, SSE, review, and tools."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from copy import deepcopy
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth import READ_SCOPE, SERVICE_SCOPE, STAFF_SCOPE, TOOL_SCOPE, authenticate, require_scopes
from .edits import apply_edits
from .errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    request_id_from,
    validation_error_handler,
)
from .persistence import Persistence
from .state import CaseRecord, CaseRegistry
from .tools import execute_lookup_patient
from .validate import validate_staff_review, validate_structured_case

log = logging.getLogger("aria.backend")


def _safe_log(request: Request, **fields: Any) -> None:
    rid = request_id_from(request)
    parts = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    log.info("request_id=%s %s", rid, parts)


def _json_response(request: Request, status_code: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body, headers={"X-Request-Id": request_id_from(request)})


async def _read_json(request: Request) -> Any:
    try:
        return await request.json()
    except Exception as exc:
        raise ApiError(400, "MALFORMED_JSON", "The request body is not valid JSON.") from exc


def _idempotency_key(request: Request, fallback: Optional[str] = None) -> str:
    header = request.headers.get("idempotency-key")
    if header and header.strip():
        return header.strip()[:128]
    if fallback:
        return fallback[:128]
    raise ApiError(400, "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key is required.")


def _format_sse(event) -> str:
    payload = json.dumps(event.envelope(), separators=(",", ":"))
    return f"id: {event.event_id}\nevent: {event.event_type}\ndata: {payload}\n\n"


def _conflict(record: CaseRecord) -> ApiError:
    return ApiError(
        409,
        "CASE_VERSION_CONFLICT",
        "The submitted case version is stale.",
        field_errors=[{"path": "/caseVersion", "message": f"Expected version {record.case_version}."}],
        extra={"latestCaseVersion": record.case_version},
    )


def create_app(conn: Any = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    app = FastAPI(title="ARIA Role 3 Backend", version="1.0.0")
    app.state.registry = CaseRegistry()
    app.state.persistence = conn if isinstance(conn, Persistence) else Persistence(conn)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("ARIA_CORS_ORIGINS", "*").split(","),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "Last-Event-ID"],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "role": "3"}

    @app.get("/api/v1/cases")
    async def list_cases(request: Request) -> JSONResponse:
        principal = authenticate(request)
        require_scopes(principal, READ_SCOPE)
        items = app.state.registry.list_ready()
        _safe_log(request, action="list_cases", count=len(items))
        return _json_response(request, 200, {"cases": items})

    @app.post("/api/v1/cases/{case_id}/structured-case")
    async def ingest_structured_case(case_id: str, request: Request) -> JSONResponse:
        principal = authenticate(request)
        require_scopes(principal, SERVICE_SCOPE)
        payload = validate_structured_case(await _read_json(request))
        if payload["caseId"] != case_id:
            raise ApiError(
                422,
                "CASE_ID_MISMATCH",
                "The case id in the path and body must match.",
                field_errors=[{"path": "/caseId", "message": "Must match the path parameter."}],
            )
        registry: CaseRegistry = app.state.registry
        record = registry.get_or_create(case_id)
        key = _idempotency_key(request, f"{case_id}-{payload['caseVersion']}")
        if key in record.ingest_keys:
            _safe_log(request, action="ingest", status="duplicate", case_id=case_id)
            return _json_response(request, 202, record.ingest_keys[key])

        incoming = int(payload["caseVersion"])
        if record.case_version >= 0 and incoming <= record.case_version:
            raise _conflict(record)

        updated = deepcopy(payload)
        if record.protected_edits:
            updated = apply_edits(updated, record.protected_edits)

        first = record.structured_case is None
        record.session_id = payload.get("sessionId")
        record.case_version = incoming
        record.structured_case = updated
        patient_ref = (payload.get("subject") or {}).get("patientReference")
        if patient_ref:
            record.linked_patient_public_id = patient_ref

        persistence: Persistence = app.state.persistence
        if record.linked_phone or patient_ref:
            lookup = None
            if patient_ref and not record.linked_phone:
                lookup = persistence.lookup_patient(
                    principal.actor_id, "CLINICIAN", patient_public_id=patient_ref
                )
                if lookup.get("patient"):
                    phone = lookup["patient"].get("phone")
                    if phone and not str(phone).startswith("["):
                        record.linked_phone = phone
            persisted = persistence.ensure_case(
                phone=record.linked_phone,
                case_public_id=case_id,
                session_public_id=record.session_id,
                case_version=incoming,
                summary=(updated.get("summary") or {}).get("oneLine"),
                actor_id=principal.actor_id,
                actor_role=principal.actor_role,
            )
            if persisted.get("case_id"):
                record.persistence_case_id = persisted["case_id"]

        event_type = "case.snapshot" if first else "case.updated"
        registry.publish(record, event_type, {"structuredCase": updated, "reviewStatus": record.review_status})
        body = {
            "status": "accepted",
            "caseId": case_id,
            "caseVersion": incoming,
            "eventType": event_type,
        }
        record.ingest_keys[key] = body
        _safe_log(request, action="ingest", status="accepted", case_id=case_id, case_version=incoming)
        return _json_response(request, 202, body)

    @app.get("/api/v1/cases/{case_id}")
    async def get_case(case_id: str, request: Request) -> JSONResponse:
        principal = authenticate(request)
        require_scopes(principal, READ_SCOPE)
        record = app.state.registry.get(case_id)
        return _json_response(request, 200, app.state.registry.snapshot(record))

    @app.get("/api/v1/cases/{case_id}/events")
    async def case_events(case_id: str, request: Request) -> StreamingResponse:
        principal = authenticate(request)
        require_scopes(principal, READ_SCOPE)
        registry: CaseRegistry = app.state.registry
        record = registry.get(case_id)
        last_id = request.headers.get("last-event-id")
        idle = float(os.environ.get("ARIA_SSE_IDLE_TIMEOUT", "15"))
        _safe_log(request, action="sse_connect", case_id=case_id, replay=bool(last_id))

        async def generate():
            queue = registry.subscribe(case_id)
            try:
                for event in registry.events_after(record, last_id):
                    yield _format_sse(event)
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=max(idle, 0.05))
                        yield _format_sse(event)
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
                        if idle <= 0.2:
                            break
                    if await request.is_disconnected():
                        break
            finally:
                registry.unsubscribe(case_id, queue)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Request-Id": request_id_from(request),
            },
        )

    @app.post("/api/v1/cases/{case_id}/reviews")
    async def submit_review(case_id: str, request: Request) -> JSONResponse:
        principal = authenticate(request)
        require_scopes(principal, STAFF_SCOPE)
        payload = validate_staff_review(await _read_json(request))
        if payload["caseId"] != case_id:
            raise ApiError(
                422,
                "CASE_ID_MISMATCH",
                "The case id in the path and body must match.",
                field_errors=[{"path": "/caseId", "message": "Must match the path parameter."}],
            )
        registry: CaseRegistry = app.state.registry
        record = registry.get(case_id)
        key = _idempotency_key(request, payload.get("idempotencyKey"))
        if key in record.review_keys:
            _safe_log(request, action="review", status="duplicate", case_id=case_id)
            return _json_response(request, 202, record.review_keys[key])
        if int(payload["baseCaseVersion"]) != record.case_version:
            raise _conflict(record)
        if record.structured_case is None:
            raise ApiError(422, "CASE_NOT_READY", "A structured case must be ingested before review.")

        edited = apply_edits(record.structured_case, payload.get("edits") or [])
        record.structured_case = edited
        if payload.get("edits"):
            record.protected_edits.extend(payload["edits"])

        action = payload["action"]
        result: dict[str, Any] = {
            "status": action,
            "caseId": case_id,
            "reviewerId": principal.actor_id,
            "baseCaseVersion": payload["baseCaseVersion"],
        }
        if action == "save_draft":
            record.review_status = "draft_saved"
        elif action == "request_more_information":
            record.review_status = "more_information_requested"
            result["questions"] = (payload.get("informationRequest") or {}).get("questions", [])
        elif action == "approve":
            if record.approved:
                result["status"] = "duplicate"
            else:
                persisted = app.state.persistence.save_approved(
                    case_public_id=case_id,
                    persistence_case_id=record.persistence_case_id,
                    clinician_id=principal.actor_id,
                    actor_role=principal.actor_role,
                    idempotency_key=key,
                    case_version=record.case_version,
                    final_triage=payload.get("finalTriage") or {},
                    edits=payload.get("edits") or [],
                    comment=payload.get("comment"),
                    structured_case=edited,
                )
                if persisted.get("error"):
                    raise ApiError(422, "APPROVAL_PERSISTENCE_FAILED", "The approved record could not be stored.")
                record.approved = True
                record.review_status = "approved"
                result["approvedRecord"] = {
                    "status": persisted.get("status"),
                    "approvedRecordPublicId": persisted.get("approved_record_public_id"),
                }
        record.case_version += 1
        result["caseVersion"] = record.case_version
        registry.publish(
            record,
            "case.review_status",
            {"reviewStatus": record.review_status, "action": action, "reviewerId": principal.actor_id},
        )
        record.review_keys[key] = result
        _safe_log(request, action="review", status=action, case_id=case_id)
        return _json_response(request, 202, result)

    @app.post("/api/v1/cases/{case_id}/tools")
    async def call_tool(case_id: str, request: Request) -> JSONResponse:
        principal = authenticate(request)
        require_scopes(principal, TOOL_SCOPE)
        body = await _read_json(request)
        if not isinstance(body, dict):
            raise ApiError(400, "MALFORMED_JSON", "The request body is not valid JSON.")
        tool = body.get("tool")
        arguments = body.get("arguments") or {}
        if tool != "lookup_patient":
            raise ApiError(422, "UNKNOWN_TOOL", "The requested tool is not available.")
        registry: CaseRegistry = app.state.registry
        record = registry.get_or_create(case_id)
        key = _idempotency_key(request, body.get("idempotencyKey") or f"tool-{case_id}-{tool}")
        result = await execute_lookup_patient(
            registry=registry,
            persistence=app.state.persistence,
            record=record,
            principal=principal,
            arguments=arguments,
            idempotency_key=key,
        )
        status_code = 200 if result.get("status") == "success" else 202
        if result.get("duplicate"):
            status_code = 200
        _safe_log(request, action="tool", tool=tool, status=result.get("status"), case_id=case_id)
        return _json_response(request, status_code, result)

    @app.get("/api/v1/patients/lookup")
    async def lookup_patient(request: Request, phone: Optional[str] = None, patientPublicId: Optional[str] = None) -> JSONResponse:
        principal = authenticate(request)
        require_scopes(principal, READ_SCOPE, TOOL_SCOPE)
        if principal.actor_role == "DISPATCHER":
            role = "DISPATCHER"
        else:
            role = "CLINICIAN"
        result = app.state.persistence.lookup_patient(
            principal.actor_id, role, phone=phone, patient_public_id=patientPublicId
        )
        status = 404 if result.get("error") == "Patient not found" else 200
        if status == 404:
            raise ApiError(404, "PATIENT_NOT_FOUND", "Patient not found.")
        _safe_log(request, action="lookup", status="ok")
        return _json_response(request, 200, result)

    @app.get("/api/v1/patients/{patient_id}/history")
    async def patient_history(patient_id: str, request: Request) -> JSONResponse:
        """Role 1 AssemblyAI HTTP-tool alias for authorised Role 4 lookup."""
        principal = authenticate(request)
        require_scopes(principal, READ_SCOPE, TOOL_SCOPE)
        role = "DISPATCHER" if principal.actor_role == "DISPATCHER" else "CLINICIAN"
        result = app.state.persistence.lookup_patient(
            principal.actor_id, role, patient_public_id=patient_id
        )
        if result.get("error") == "Patient not found":
            raise ApiError(404, "PATIENT_NOT_FOUND", "Patient not found.")
        _safe_log(request, action="history", status="ok")
        return _json_response(request, 200, result)

    return app
