BEGIN;

-- PostgreSQL returns NULL from uuid_extract_version() for UUIDs outside the
-- RFC 9562 variant. A CHECK written only as `uuid_extract_version(...) = 7`
-- therefore evaluates to UNKNOWN for those values, and SQL CHECK constraints
-- accept UNKNOWN. Make the persisted decision boundary explicitly two-valued.
ALTER TABLE architecture_core.assessment_recheck_request
    DROP CONSTRAINT assessment_recheck_request_decision_uuid_version;

ALTER TABLE architecture_core.assessment_recheck_request
    ADD CONSTRAINT assessment_recheck_request_decision_uuid_version
    CHECK (uuid_extract_version(decision_request_id) IS NOT DISTINCT FROM 7);

COMMENT ON CONSTRAINT assessment_recheck_request_decision_uuid_version
ON architecture_core.assessment_recheck_request IS
'Every persisted reassessment decision identifier must be an RFC 9562 UUIDv7. uuid_extract_version returns NULL for non-RFC variants, so IS NOT DISTINCT FROM 7 keeps the invariant fail-closed rather than allowing SQL CHECK UNKNOWN.';

COMMIT;
