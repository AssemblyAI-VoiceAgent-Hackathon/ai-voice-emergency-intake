"""Server-side permission map for Role 4 persistence calls.

Role 3 will later bind these roles to authenticated tokens. Until that PR
exists, callers must pass actor_id and actor_role explicitly.
"""

from __future__ import annotations


class Role:
    CLINICIAN = "CLINICIAN"
    DISPATCHER = "DISPATCHER"
    AGENT_SYSTEM = "AGENT_SYSTEM"
    COMPLIANCE_DPO = "COMPLIANCE_DPO"


PERMISSIONS = {
    Role.CLINICIAN: {
        "lookup_patient",
        "create_case",
        "create_session",
        "approve_record",
        "read_case",
        "read_audit",
    },
    Role.DISPATCHER: {
        "lookup_patient_redacted",
        "read_case",
    },
    Role.AGENT_SYSTEM: {
        "lookup_patient",
        "create_case",
        "create_session",
        "append_note",
        "read_audit",
    },
    Role.COMPLIANCE_DPO: {
        "read_audit",
        "purge_retention",
        "lookup_patient_redacted",
    },
}

REDACTED_ROLES = {Role.DISPATCHER, Role.COMPLIANCE_DPO}


def authorize(role: str, action: str) -> None:
    if action not in PERMISSIONS.get(role, set()):
        raise PermissionError(f"Role '{role}' denied for '{action}'")


def is_redacted_role(role: str) -> bool:
    return role in REDACTED_ROLES
