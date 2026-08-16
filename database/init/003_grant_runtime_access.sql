\set ON_ERROR_STOP on

REVOKE ALL ON SCHEMA architecture_core FROM PUBLIC;
GRANT USAGE ON SCHEMA architecture_core TO ea_runtime;

-- The database login proves connectivity only. Application-table authority is
-- intentionally absent: an untrusted client can set custom GUC values, so RLS
-- context alone is not an authorization boundary. Future domain access is
-- granted only to purpose-bound command/query functions after the service has
-- verified and bound Keyverse issuer, audience, tenant, and role claims.
REVOKE ALL PRIVILEGES
ON ALL TABLES IN SCHEMA architecture_core
FROM ea_runtime;

REVOKE EXECUTE
ON ALL FUNCTIONS IN SCHEMA architecture_core
FROM PUBLIC, ea_runtime;
