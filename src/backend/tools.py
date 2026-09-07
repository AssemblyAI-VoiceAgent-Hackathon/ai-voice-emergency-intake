"""JSON-Schema tool calling for authorised Role 4 operations."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from .auth import Principal
from .errors import ApiError
from .persistence import Persistence
from .state import CaseRecord, CaseRegistry
from .validate import validate_tool_arguments

log = logging.getLogger("aria.backend")


async def execute_lookup_patient(
    *,
    registry: CaseRegistry,
    persistence: Persistence,
    record: CaseRecord,
    principal: Principal,
    arguments: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    existing = record.tool_keys.get(idempotency_key)
    if existing:
        log.info("tool_duplicate tool=lookup_patient case_id=%s", record.case_id)
        return {**existing, "duplicate": True}

    arguments = validate_tool_arguments("lookup_patient", arguments)
    pending = {
        "tool": "lookup_patient",
        "status": "pending",
        "idempotencyKey": idempotency_key,
    }
    registry.publish(record, "case.tool_status", pending)

    simulate = arguments.get("simulate")
    timeout_s = float(os.environ.get("ARIA_TOOL_TIMEOUT_SEC", "5"))
    if simulate == "timeout":
        timeout_s = min(timeout_s, 0.05)

    async def _run() -> dict[str, Any]:
        if simulate == "timeout":
            await asyncio.sleep(0.2)
            return {}
        if simulate == "failure":
            raise RuntimeError("simulated tool failure")
        role = principal.actor_role if principal.actor_role != "AGENT_SYSTEM" else "CLINICIAN"
        return persistence.lookup_patient(
            principal.actor_id,
            role,
            phone=arguments.get("phone"),
            patient_public_id=arguments.get("patientPublicId"),
        )

    try:
        result = await asyncio.wait_for(_run(), timeout=timeout_s)
        status = "success"
        payload: dict[str, Any] = {
            "tool": "lookup_patient",
            "status": status,
            "idempotencyKey": idempotency_key,
            "result": result,
        }
        if result.get("error") == "Patient not found":
            payload["status"] = "success"
        elif result.get("patient"):
            record.linked_patient_public_id = result["patient"].get("public_id")
            phone = result["patient"].get("phone")
            if phone and not str(phone).startswith("["):
                record.linked_phone = phone
        registry.publish(record, "case.tool_status", payload)
        record.tool_keys[idempotency_key] = payload
        return payload
    except asyncio.TimeoutError:
        payload = {
            "tool": "lookup_patient",
            "status": "timeout",
            "idempotencyKey": idempotency_key,
        }
        registry.publish(record, "case.tool_status", payload)
        record.tool_keys[idempotency_key] = payload
        raise ApiError(504, "TOOL_TIMEOUT", "The tool call timed out.")
    except ApiError:
        raise
    except Exception:
        payload = {
            "tool": "lookup_patient",
            "status": "failure",
            "idempotencyKey": idempotency_key,
        }
        registry.publish(record, "case.tool_status", payload)
        record.tool_keys[idempotency_key] = payload
        log.info("tool_failure tool=lookup_patient case_id=%s", record.case_id)
        raise ApiError(422, "TOOL_FAILED", "The tool call failed.")
