BEGIN;

ALTER FUNCTION architecture_core.reject_assessment_recheck_request_mutation()
    SET search_path = pg_catalog;

REVOKE ALL
ON FUNCTION architecture_core.reject_assessment_recheck_request_mutation()
FROM PUBLIC;

REVOKE ALL
ON FUNCTION architecture_core.request_data_management_assessment_recheck(
    uuid,
    uuid,
    uuid,
    timestamptz
)
FROM PUBLIC;

COMMENT ON FUNCTION architecture_core.reject_assessment_recheck_request_mutation() IS
'Immutable-history guard for assessment reassessment-request evidence. The function pins search_path to pg_catalog and PUBLIC execution is revoked so later maintenance cannot accidentally expand the mutation boundary.';

COMMIT;
