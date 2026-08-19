BEGIN;

REVOKE ALL
ON FUNCTION architecture_core.accept_data_management_improvement_evidence(
    uuid,
    uuid,
    text,
    text,
    text,
    uuid,
    timestamptz
)
FROM PUBLIC;

REVOKE ALL
ON FUNCTION architecture_core.reject_data_management_closure_mutation()
FROM PUBLIC;

ALTER FUNCTION architecture_core.reject_data_management_closure_mutation()
    SET search_path = pg_catalog;

COMMENT ON FUNCTION architecture_core.accept_data_management_improvement_evidence(
    uuid,
    uuid,
    text,
    text,
    text,
    uuid,
    timestamptz
) IS
'Accepts only authoritative or observed tenant-local Semantic Data Portal assessment evidence with a receipt-bound digest, records immutable milestone completion and transactional outbox evidence atomically, returns an assessment-recheck next action when all projected gaps are closed, and makes exact UUIDv7 decision replay deterministic. PUBLIC execution is revoked; this database-only slice grants no runtime writer authority until an authenticated application boundary is implemented.';

COMMIT;