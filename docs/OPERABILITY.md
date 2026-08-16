# Operability

## Initial service objectives

- `/health` reports process liveness only.
- `/ready` requires database connectivity, applied migrations, and valid
  contract resources.
- outbox backlog, publish age, failure count, and projection lag are mandatory
  metrics.
- all commands carry correlation and causation identifiers.

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
