# Operability

## Initial service objectives

- Start `ea-core` on `0.0.0.0:$PORT`.
- `/health` reports process liveness only. Next action: call `/ready`.
- `/ready` is fail-closed and returns 200 only when both dependency dimensions
  are proven at request time:
  - `contract_ready`: the installed `cwl-context-contracts` distribution is the
    exact version supported by this service. The current foundation supports
    `0.1.0`; absence or version mismatch is non-passing.
  - `database_ready`: the documented `EA_DATABASE_DSN` authenticates as the
    `ea_runtime` role to database `ea_core`, the expected `architecture_core`
    schema and foundation objects exist, and the runtime role still lacks
    direct `SELECT` authority on application tables.
- A missing/malformed DSN, unavailable `psql` client, connection/query failure,
  probe timeout, missing schema object, unexpected table privilege, missing
  Context Graph contract, or contract version mismatch keeps `/ready` at 503.
  Inspect the exact false boolean, repair that dependency, then retry `/ready`.
- The database readiness probe uses libpq environment variables derived from the
  configured DSN and never places the DSN or password in the `psql` argument
  vector. Production deployments must provide the DSN through a managed secret
  and include a compatible PostgreSQL client in the service image.
- outbox backlog, publish age, failure count, and projection lag are mandatory
  metrics.
- all commands carry correlation and causation identifiers.

## Contract release dependency

`enterprise-architecture-core` does not treat a source checkout, mutable branch,
or unreleased Context Graph build as an immutable interoperability dependency.
Until a compatible `cwl-context-contracts==0.1.0` release is installed, a healthy
PostgreSQL instance can make `database_ready=true` while `contract_ready=false`;
that 503 is intentional. Once the protected contract release exists, install the
exact supported distribution and re-run the process-level readiness acceptance
before promoting this service.

## Backup and recovery

Authoritative PostgreSQL data requires encrypted backups, point-in-time
recovery, periodic restore rehearsal, and documented regional recovery. Graph
or search projections are rebuilt from events and are not backup authorities.

## Deployment

The initial Compose profile is development-only. Production deployment must use
managed secrets, encrypted transport, tenant isolation, resource limits,
OpenTelemetry, and controlled migration execution.

## Incident response

Runbooks must cover invalid lifecycle bulk import, outbox backlog, projection
poison events, Keyverse verification failure, tenant isolation alerts, and
erroneous transformation execution with compensating changes.
