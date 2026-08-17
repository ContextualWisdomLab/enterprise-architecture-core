# Operability

## Service objectives

- Start `ea-core` on `0.0.0.0:$PORT`.
- `/health` reports process liveness only. Next action: call `/ready`.
- `/ready` returns 200 only when the installed `cwl-context-contracts` version and the PostgreSQL runtime-role boundary are proven. Missing/malformed DSN, `psql` failure/timeout, missing schema, unexpected table privilege, missing Context Graph contract or version mismatch remains 503.
- Database probes use libpq environment variables and never place the DSN/password in argv. Production deployments provide the DSN through managed secrets and a compatible PostgreSQL client.
- Outbox backlog, publish age, failure count and projection lag are mandatory metrics.

## Authenticated target-state planner

The planner is a separate fail-closed serving boundary. A healthy `/ready` does not manufacture Keyverse authorization state: protected planner reads additionally require complete `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, `EA_ROLE_CLAIM` and `EA_READ_ROLES` configuration plus a current valid bearer.

Operational responses are actionable and secret-safe:

- `401 authorization_required` or `invalid_token`: acquire/refresh a Keyverse token and verify issuer/audience/key/clock configuration;
- `403 forbidden`: obtain an approved EA read role instead of widening the service allow-list ad hoc;
- `400 invalid_planner_request`: provide one technology UUID, explicit `valid_at`/`recorded_at`, and horizon 1..3650;
- `503 planner_unavailable`: repair fail-closed Keyverse or database configuration;
- `503 planner_query_failed`: keep the decision pending and restore the purpose-bound database query port; never fall back to direct table/projector SQL.

JWKS retrieval must remain HTTPS under the configured issuer origin/path, no-redirect, bounded and timeout-limited. Signing-key/network failure is non-passing. Do not log bearer values. The `ea_runtime` login must retain no application-table privilege and no direct execute privilege on the underlying target-state projector; only `read_technology_target_state_plan(...)` is granted.

## Contract release dependency

`enterprise-architecture-core` does not treat a source checkout, mutable branch or unreleased Context Graph build as an immutable interoperability dependency. Until compatible `cwl-context-contracts==0.1.0` is installed, a healthy database can still yield `contract_ready=false`; that 503 is intentional. Install the exact protected contract distribution and rerun process/read acceptance before promotion.

## Protected integration evidence

A green workflow is evidence only for the exact integration candidate that executed it. Before merge/release/deployment, re-fetch the default branch and live rules and prove the intended integration ref is protected. After any base/default change, generate a fresh candidate and rerun every applicable repository/security/package gate; predecessor checks/reviews do not transfer.

## Backup and recovery

Authoritative PostgreSQL data requires encrypted backups, point-in-time recovery, periodic restore rehearsal and documented regional recovery. Graph/search projections are rebuilt from events and are not backup authorities.

## Deployment

The Compose profile is development-only. Production deployment requires managed secrets, encrypted transport, tenant isolation, resource limits, OpenTelemetry and controlled migrations. Treat Keyverse issuer/JWKS/audience/claim/role configuration as versioned deployment configuration, not user-supplied request data.

## Incident response

Runbooks cover invalid lifecycle imports, outbox backlog, projection poison events, Keyverse/JWKS verification failure, tenant-isolation alerts, purpose-bound query-port privilege drift and erroneous transformation execution with compensating changes. A security incident involving tokens or database credentials requires rotation through the owning secret/identity system; EA events/context bundles must not contain those values.
