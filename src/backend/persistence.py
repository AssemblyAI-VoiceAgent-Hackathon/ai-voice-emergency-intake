"""Role 4 adapter. Role 5 never writes to the database directly."""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.data import (
    Role,
    create_case_authorised,
    create_session_authorised,
    init_db,
    lookup_patient_authorised,
    save_approved_record_authorised,
    seed_synthetic_data,
)

log = logging.getLogger("aria.backend")


class Persistence:
    def __init__(self, conn: Any = None) -> None:
        self.conn = conn if conn is not None else init_db()
        seed_synthetic_data(self.conn)

    def lookup_patient(
        self,
        actor_id: str,
        actor_role: str,
        phone: Optional[str] = None,
        patient_public_id: Optional[str] = None,
    ) -> dict[str, Any]:
        result = lookup_patient_authorised(
            self.conn,
            actor_id,
            actor_role,
            phone=phone,
            patient_public_id=patient_public_id,
        )
        log.info("role4_lookup actor_role=%s found=%s", actor_role, "error" not in result)
        return result

    def ensure_case(
        self,
        *,
        phone: Optional[str],
        case_public_id: str,
        session_public_id: Optional[str],
        case_version: int,
        summary: Optional[str],
        actor_id: str,
        actor_role: str,
    ) -> dict[str, Any]:
        if not phone:
            return {"error": "Patient phone is required to persist a case"}
        created = create_case_authorised(
            self.conn,
            phone,
            summary=summary,
            actor_id=actor_id,
            actor_role=actor_role if actor_role in {Role.AGENT_SYSTEM, Role.CLINICIAN} else Role.AGENT_SYSTEM,
            public_id=case_public_id,
            case_version=case_version,
        )
        if created.get("error"):
            return created
        if session_public_id:
            create_session_authorised(
                self.conn,
                case_id=created.get("case_id"),
                case_public_id=case_public_id,
                public_id=session_public_id,
                actor_id=actor_id,
                actor_role=actor_role if actor_role in {Role.AGENT_SYSTEM, Role.CLINICIAN} else Role.AGENT_SYSTEM,
                transcript_ref="SYN:role3-session-ref",
            )
        return created

    def save_approved(
        self,
        *,
        case_public_id: str,
        persistence_case_id: Optional[int],
        clinician_id: str,
        actor_role: str,
        idempotency_key: str,
        case_version: int,
        final_triage: dict[str, Any],
        edits: list[dict[str, Any]],
        comment: Optional[str],
        structured_case: dict[str, Any],
    ) -> dict[str, Any]:
        summary = (structured_case.get("summary") or {}).get("oneLine") or "SYN:Approved case"
        complaint = (structured_case.get("chiefComplaint") or {}).get("text") or summary
        return save_approved_record_authorised(
            self.conn,
            case_id=persistence_case_id,
            case_public_id=case_public_id,
            esi_level=None,
            chief_complaint=complaint,
            sbar_situation=summary,
            sbar_background=complaint,
            sbar_assessment=summary,
            sbar_recommendation="SYN:Human reviewer approved the record",
            attending_clinician_id=clinician_id,
            actor_role=actor_role,
            notes=comment,
            decision="approved",
            idempotency_key=idempotency_key,
            final_triage_code=final_triage.get("code", ""),
            final_triage_label=final_triage.get("label", ""),
            final_triage_rationale=final_triage.get("rationale"),
            case_version=case_version,
            edits=edits,
        )
