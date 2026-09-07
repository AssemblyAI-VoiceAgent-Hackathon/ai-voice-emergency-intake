"""Role 4 persistence: authorised lookup, approved records, audit, and fixtures.

This package does not depend on Role 1 or Role 3. Role 3 can later call the
functions exported here from FastAPI handlers. `init_db()` uses Supabase when
`SUPABASE_URL` is set and SQLite otherwise.
"""

from .client import is_configured as supabase_configured
from .crypto import SYN_PREFIX, phone_hash
from .fixtures import (
    NOT_FOUND_PHONE,
    export_fixtures_to_json,
    get_all_patients_by_scenario,
    get_notes_for_patient,
    get_patient_by_id,
    get_patient_by_phone,
    get_patient_by_public_id,
    load as load_fixtures,
    reset as reset_fixtures,
    validate as validate_fixtures,
)
from .rbac import Role
from .schema import CURRENT_SCHEMA_VERSION, get_current_migration_version, get_migration_history, migrate_db
from .store import (
    append_note_authorised,
    create_case_authorised,
    create_session_authorised,
    get_audit_trail,
    get_case_lineage,
    get_connection,
    get_stats,
    init_db,
    lookup_patient_authorised,
    purge_retention_authorised,
    read_audit_authorised,
    read_case_authorised,
    save_approved_record_authorised,
    seed_synthetic_data,
    verify_audit_integrity,
)
from .supabase_store import check_connection as check_supabase, table_status

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "NOT_FOUND_PHONE",
    "Role",
    "SYN_PREFIX",
    "append_note_authorised",
    "check_supabase",
    "create_case_authorised",
    "create_session_authorised",
    "export_fixtures_to_json",
    "get_all_patients_by_scenario",
    "get_audit_trail",
    "get_case_lineage",
    "get_connection",
    "get_current_migration_version",
    "get_migration_history",
    "get_notes_for_patient",
    "get_patient_by_id",
    "get_patient_by_phone",
    "get_patient_by_public_id",
    "get_stats",
    "init_db",
    "load_fixtures",
    "lookup_patient_authorised",
    "migrate_db",
    "phone_hash",
    "purge_retention_authorised",
    "read_audit_authorised",
    "read_case_authorised",
    "reset_fixtures",
    "save_approved_record_authorised",
    "seed_synthetic_data",
    "supabase_configured",
    "table_status",
    "validate_fixtures",
    "verify_audit_integrity",
]
