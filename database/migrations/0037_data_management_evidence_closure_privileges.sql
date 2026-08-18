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

COMMENT ON FUNCTION architecture_core.accept_data_management_improvement_evidence(
    uuid,
    uuid,
    text,
    text,
    text,
    uuid,
    timestamptz
) IS
'Purpose-bound data-management evidence-closure command. PUBLIC execution is revoked; this database-only slice grants no runtime writer authority until an authenticated application boundary is implemented.';

COMMIT;
