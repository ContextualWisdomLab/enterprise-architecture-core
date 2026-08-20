\set ON_ERROR_STOP on

REVOKE ALL ON SCHEMA architecture_core FROM PUBLIC;
GRANT USAGE ON SCHEMA architecture_core TO ea_runtime;

-- The database login proves connectivity only. Application-table authority is
-- intentionally absent: an untrusted client can set custom GUC values, so RLS
-- context alone is not an authorization boundary. Domain access is granted only
-- to purpose-bound functions after the service has verified and bound Keyverse
-- signature, issuer, audience, expiration, tenant, and role claims.
REVOKE ALL PRIVILEGES
ON ALL TABLES IN SCHEMA architecture_core
FROM ea_runtime;

-- Migrations may grant a new purpose-bound function when ea_runtime already
-- exists. Normalize clean-install authority after every migration, then restore
-- the complete public runtime surface explicitly so stale migration grants can
-- never accumulate into deployment authority.
REVOKE EXECUTE
ON ALL FUNCTIONS IN SCHEMA architecture_core
FROM PUBLIC, ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.read_technology_target_state_plan(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.approve_target_state(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.schedule_transformation(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.start_scheduled_transformation(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.complete_started_transformation(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.record_target_state_verification(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid,
    text
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.read_target_state_monitoring_status(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.record_target_state_replan(
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    timestamptz,
    text,
    text,
    uuid
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.request_data_management_assessment_recheck_for_tenant(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.read_data_management_assessment_recheck_status(
    uuid,
    uuid
)
TO ea_runtime;

GRANT EXECUTE
ON FUNCTION architecture_core.read_portfolio_assessment_for_tenant(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    text,
    text
)
TO ea_runtime;
