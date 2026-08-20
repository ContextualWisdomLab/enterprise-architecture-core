# Operability

## Service objectives

- Start `ea-core` on `0.0.0.0:$PORT`.
- `/health` reports process liveness only. Next action: call `/ready`.
- `/ready` returns 200 only when the installed `cwl-context-contracts` version and the PostgreSQL runtime-role boundary are proven. Missing/malformed DSN, `psql` failure/timeout, missing schema, unexpected table privilege, missing Context Graph contract or version mismatch remains 503.
- Database probes and governed request ports use documented libpq environment variables and never place the DSN/password in argv. Production deployments provide the DSN through managed secrets and a compatible PostgreSQL client.
- Outbox backlog, publish age, failure count, projection lag, failed governed commands, verification gaps, and stale monitoring evidence are mandatory operational signals.

## Hot-write capacity snapshot

Run the read-only snapshot from an approved database owner or observability
connection, not from `ea_runtime`:

```bash
PGHOST=<host> PGPORT=<port> PGUSER=<approved_operator> PGDATABASE=<database> \\
  psql --set=tenant_id=<tenant_uuid> \\
  --file=database/reports/hot_write_capacity_snapshot.sql
```

Repeat the command for the same tenant at comparable intervals. Compare
`row_count`, `active_work_count`, `queue_lag_seconds`, `hot_partition_bucket`,
relation/index sizes, and the cumulative tuple/WAL counters. A negative queue
lag means the source timestamp is in the future relative to the snapshot and
must be investigated; do not clamp it. The report is measurement evidence, not
a production capacity limit or proof that physical HASH/LIST partitions are
deployed. Do not grant the runtime role direct table access to run it.

## Purpose-bound Keyverse authorization

A healthy `/ready` does not manufacture Keyverse authorization state. Every `/v1/` operation additionally requires complete OIDC configuration and its own purpose-bound role allow-list. Configure `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, and `EA_ROLE_CLAIM`, plus:

- planner reads: `EA_READ_ROLES`;
- human approval: `EA_APPROVAL_ROLES`;
- milestone scheduling: `EA_SCHEDULE_ROLES`;
- transformation start: `EA_START_ROLES`;
- transformation completion: `EA_COMPLETE_ROLES`;
- target-state verification: `EA_VERIFY_ROLES`;
- post-verification monitoring: `EA_MONITOR_ROLES`.

Roles do not inherit from one another. A missing operation-specific allow-list keeps only that operation unavailable. Do not widen another allow-list to work around a denied request.

JWKS retrieval must remain HTTPS under the configured issuer origin/path, no-redirect, bounded, timeout-limited, and fail-closed. Signing-key/network failure is non-passing. Do not log bearer values, governed request bodies, decision reasons, or database credentials. PostgreSQL URI `sslsni` configuration maps to libpq `PGSSLSNI`.

## Authenticated target-state planner

For `GET /v1/technology-target-state-plans/{technology_version_id}`:

- `401 authorization_required` or `invalid_token`: acquire/refresh a Keyverse token and verify issuer/audience/key/clock configuration;
- `403 forbidden`: obtain an approved EA read role instead of widening the service allow-list ad hoc;
- `400 invalid_planner_request`: provide one technology UUID, explicit `valid_at`/`recorded_at`, and horizon 1..3650;
- `503 planner_unavailable`: repair fail-closed Keyverse or database configuration;
- `503 planner_query_failed`: keep the decision pending and restore the purpose-bound database query port; never fall back to direct table/projector SQL.

Planner output remains non-mutating evidence. `approve_target_state` is a recommendation until an independently authorized approval command succeeds.

## Governed transformation lifecycle

The transformation lifecycle uses separate human or operator authority at every state-changing boundary. Each command derives the actor from the verified Keyverse identity, requires a canonical UUIDv7 decision request and evidence reference, records explicit business-effective and system-recorded time, and commits authoritative history plus its transactional outbox event atomically. Exact retries are idempotent; conflicting reuse of a decision request fails closed.

### Approval

For `POST /v1/architecture-transformations/{architecture_transformation_id}/approval`, send UUIDv7 `decision_request_id`/`evidence_record_id`, offset-aware `effective_at`, and a bounded human `decision_reason_text`. A new approval returns 201; an exact replay returns 200 with the original immutable receipt. The resulting next action is `schedule_transformation`.

### Scheduling

For `POST /v1/architecture-transformations/{architecture_transformation_id}/schedule`, also provide UUIDv7 `initiative_milestone_id`. Scheduling may bind only the current approved authoritative transformation to an active authoritative milestone of the same remediation initiative. The milestone remains the target-date source of truth. A successful receipt directs `start_transformation`; this boundary does not create project/task execution authority.

### Start

For `POST /v1/architecture-transformations/{architecture_transformation_id}/start`, the current transformation must already have an accepted schedule. A successful append records authoritative `started` history plus the start event and directs `monitor_transformation`.

### Completion

For `POST /v1/architecture-transformations/{architecture_transformation_id}/complete`, only the current authoritative started transformation can advance. Completion records authoritative `completed` history and directs `verify_target_state`; it never means the target state has been verified.

### Target-state verification

For `POST /v1/architecture-transformations/{architecture_transformation_id}/verification`, an authorized verifier records `verification_outcome_code` as exactly `verified` or `gap_detected` against explicit evidence. `verified` directs `monitor_target_state`; `gap_detected` directs `replan_target_state`. Inferred, proposed, planner, or LLM output cannot silently become authoritative verification evidence.

For all governed commands:

- `401 authorization_required` or `invalid_token`: repair Keyverse identity/token configuration;
- `403 forbidden`: obtain the operation-specific role rather than reusing a sibling role;
- `400 invalid_*_request`: correct canonical identity, time, body, or state-transition inputs;
- `503 *_unavailable`: restore the operation-specific role/OIDC configuration or purpose-bound database port;
- `503 *_command_failed`: preserve the decision request ID, determine the causal database/state/idempotency conflict, and retry only after it is resolved. Never synthesize a receipt or mutate application tables directly.

## Post-verification monitoring

`GET /v1/architecture-transformations/{architecture_transformation_id}/monitoring` is read-only. Supply explicit `valid_at` and `recorded_at`; optionally supply `max_evidence_age_days` from 1 through 3650, default 90. The response binds one terminal verification/gap record to the requested transformation and returns its evidence UUID, valid/system timestamps, integer evidence age, monitoring state, and deterministic next action:

- `current` -> `continue_monitoring`;
- `stale` -> `collect_new_target_state_evidence`;
- `gap_detected` -> `replan_target_state`.

Monitoring does not reopen or rewrite terminal transformation history. A malformed request, unavailable monitor role/port, database failure, evidence identity drift, invalid temporal evidence, negative/non-integer evidence age, or state/action inconsistency fails closed. Operators must not reinterpret stale or gap evidence as verified-current success.

## PostgreSQL authority boundary

The `ea_runtime` login has no direct application-table or underlying-projector authority. After service-side Keyverse verification it may execute only the purpose-bound functions needed by implemented operations:

- `read_technology_target_state_plan(...)`;
- `approve_target_state(...)`;
- `schedule_transformation(...)`;
- `start_scheduled_transformation(...)`;
- `complete_started_transformation(...)`;
- `record_target_state_verification(...)`;
- `read_target_state_monitoring_status(...)`.

Each wrapper transaction-locally binds the already verified tenant UUID before tenant-scoped work. The subprocess removes inherited `PG*` state before reconstructing allow-listed connection authority from the validated EA DSN. No runtime path is allowed to query foreign-product application tables directly.

## Contract release dependency

`enterprise-architecture-core` does not treat a source checkout, mutable branch, or unreleased Context Graph build as an immutable interoperability dependency. Until the compatible `cwl-context-contracts` distribution is installed, a healthy database can still yield `contract_ready=false`; that 503 is intentional. Install the exact protected contract distribution and rerun process/read/full-lifecycle/monitoring acceptance before promotion.

## Protected integration evidence

A green workflow is evidence only for the exact integration candidate that executed it. Before merge/release/deployment, re-fetch the default branch and live rules and prove the intended integration ref is protected. After any base/default change, generate a fresh candidate and rerun every applicable repository/security/package gate; predecessor checks/reviews do not transfer.

## Backup and recovery

Authoritative PostgreSQL data requires encrypted backups, point-in-time recovery, periodic restore rehearsal, and documented regional recovery. Restore acceptance must preserve transformation history, scheduling bindings, idempotency receipts, verification evidence, monitoring source evidence, and corresponding transactional outbox records consistently. Graph/search projections are rebuildable from governed events and are not backup authorities.

## Deployment

The Compose profile is development-only. Production deployment requires managed secrets, encrypted transport, tenant isolation, resource limits, OpenTelemetry, controlled migrations, backup/restore validation, and purpose-bound Keyverse configuration for every implemented operation. Treat issuer/JWKS/audience/claim and all role allow-lists as versioned deployment configuration, never user-supplied request data.

## Incident response

Runbooks cover invalid lifecycle imports, outbox backlog, projection poison events, Keyverse/JWKS verification failure, tenant-isolation alerts, purpose-bound privilege drift, idempotency conflicts, schedule/state-transition conflicts, approval/completion/verification history-outbox inconsistency, unexpected verification gaps, stale-evidence spikes, and erroneous transformation execution with compensating governed changes. A security incident involving tokens or database credentials requires rotation through the owning secret/identity system; EA events/context bundles must not contain those values.
