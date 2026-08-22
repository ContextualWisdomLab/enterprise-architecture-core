# Operability

## Service objectives

- Start `ea-core` on `0.0.0.0:$PORT`.
- `/health` reports process liveness only. Next action: call `/ready`.
- `/ready` returns 200 only when the installed `cwl-context-contracts` version and the PostgreSQL runtime-role boundary are proven. Missing/malformed DSN, `psql` failure/timeout, missing schema, unexpected table privilege, missing Context Graph contract or version mismatch remains 503.
- Database probes use documented libpq environment variables and never place the DSN/password in argv. Production deployments provide the DSN through managed secrets and a compatible PostgreSQL client.
- Outbox backlog, publish age, failure count and projection lag are mandatory metrics.

## Authenticated target-state planner

The planner is a separate fail-closed serving boundary. A healthy `/ready` does not manufacture Keyverse authorization state: protected planner reads additionally require complete `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, `EA_ROLE_CLAIM` and `EA_READ_ROLES` configuration plus a current valid bearer.

Operational responses are actionable and secret-safe:

- `401 authorization_required` or `invalid_token`: acquire/refresh a Keyverse token and verify issuer/audience/key/clock configuration;
- `403 forbidden`: obtain an approved EA read role instead of widening the service allow-list ad hoc;
- `400 invalid_planner_request`: provide one technology UUID, explicit `valid_at`/`recorded_at`, and horizon 1..3650;
- `503 planner_unavailable`: repair fail-closed Keyverse or database configuration;
- `503 planner_query_failed`: keep the decision pending and restore the purpose-bound database query port; never fall back to direct table/projector SQL.

## Governed target-state approval

Approval is a distinct mutation boundary, not an automatic continuation of planner output. Configure `EA_APPROVAL_ROLES` separately from `EA_READ_ROLES`; missing approval-role configuration keeps the command unavailable even when planner reads are healthy.

For `POST /v1/architecture-transformations/{architecture_transformation_id}/approval`:

- `401 authorization_required` or `invalid_token`: acquire/refresh a current Keyverse token and verify issuer/audience/key/clock configuration;
- `403 forbidden`: obtain an explicitly approved EA target-state approval role; do not widen read roles or reuse another product's authorization;
- `400 invalid_approval_request`: resend strict `application/json` containing UUIDv7 `decision_request_id`/`evidence_record_id`, offset-aware `effective_at`, and a bounded human `decision_reason_text`; actor is derived from the verified identity and is never caller-supplied;
- `503 approval_unavailable`: repair approval-role/OIDC configuration or the purpose-bound database command port before retrying;
- `503 approval_command_failed`: refresh the target-state plan, preserve the exact decision request ID, and retry only after the causal database/decision conflict is understood. Never synthesize a successful receipt or mutate tables directly.

A new approval returns 201; an exact idempotent replay returns 200 with the original immutable receipt. A decision request reused for different meaning is a failed command. Authoritative transformation history and its `org.contextualwisdomlab.ea.transformation.approved.v1` outbox event commit atomically, so operators must treat either side missing on replay as integrity failure rather than reconstructing evidence manually. Actor and reason remain in authorized audit history; the outbound event deliberately omits those private fields.

JWKS retrieval must remain HTTPS under the configured issuer origin/path, no-redirect, bounded and timeout-limited. Signing-key/network failure is non-passing. Do not log bearer values, approval request bodies, decision reasons, or database credentials. The `ea_runtime` login must retain no application-table privilege and no direct execute privilege on underlying projectors; only `read_technology_target_state_plan(...)` and `approve_target_state(...)` are granted. PostgreSQL URI `sslsni` configuration must map to libpq `PGSSLSNI`.

## Contract release dependency

`enterprise-architecture-core` does not treat a source checkout, mutable branch or unreleased Context Graph build as an immutable interoperability dependency. Until compatible `cwl-context-contracts==0.1.0` is installed, a healthy database can still yield `contract_ready=false`; that 503 is intentional. Install the exact protected contract distribution and rerun process/read/approval acceptance before promotion.

## Protected integration evidence

A green workflow is evidence only for the exact integration candidate that executed it. Before merge/release/deployment, re-fetch the default branch and live rules and prove the intended integration ref is protected. After any base/default change, generate a fresh candidate and rerun every applicable repository/security/package gate; predecessor checks/reviews do not transfer.

## Backup and recovery

Authoritative PostgreSQL data, including transformation history and decision-request idempotency evidence, requires encrypted backups, point-in-time recovery, periodic restore rehearsal and documented regional recovery. Graph/search projections are rebuilt from events and are not backup authorities. Restore rehearsal must prove approval history and corresponding outbox evidence remain consistent.

## Deployment

The Compose profile is development-only. Production deployment requires managed secrets, encrypted transport, tenant isolation, resource limits, OpenTelemetry and controlled migrations. Treat Keyverse issuer/JWKS/audience/claim/read-role/approval-role configuration as versioned deployment configuration, not user-supplied request data.

## Incident response

Runbooks cover invalid lifecycle imports, outbox backlog, projection poison events, Keyverse/JWKS verification failure, tenant-isolation alerts, purpose-bound read/command privilege drift, idempotency conflicts, approval history/outbox inconsistency and erroneous transformation execution with compensating changes. A security incident involving tokens or database credentials requires rotation through the owning secret/identity system; EA events/context bundles must not contain those values.
