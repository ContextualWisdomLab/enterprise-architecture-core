\set ON_ERROR_STOP on

REVOKE ALL ON SCHEMA architecture_core FROM PUBLIC;
GRANT USAGE ON SCHEMA architecture_core TO ea_runtime;

-- Apply the secure default to the identity executing deployment bootstrap. This
-- avoids hard-coding ea_owner while still covering compose (ea_owner), CI
-- acceptance (ea_app), and a separately named production migration owner.
ALTER DEFAULT PRIVILEGES
REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- The database login proves connectivity only. Application-table authority is
-- intentionally absent: an untrusted client can set custom GUC values, so RLS
-- context alone is not an authorization boundary. Domain access is granted only
-- to purpose-bound functions after the service has verified and bound Keyverse
-- signature, issuer, audience, expiration, tenant, and role claims.
REVOKE ALL PRIVILEGES
ON ALL TABLES IN SCHEMA architecture_core
FROM ea_runtime;

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
