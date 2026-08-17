# API Contract

The implemented OpenAPI contract is in `contracts/openapi.json`.

Start the `ea-core` process, call `GET /health`, then call `GET /ready`. Use
the 503 payload fields to repair the failing dependency before sending tenant
traffic.

## Implemented read surface

`GET /v1/technology-target-state-plans/{technology_version_id}` is the first
buyer-facing authenticated read. Supply explicit `valid_at` and `recorded_at`
RFC 3339 timestamps and, optionally, `planning_horizon_days` from 1 through
3650. The response preserves lifecycle impact, affected application/capability,
receipt-backed foreign evidence, remediation initiative, target scenario,
transformation state, decision readiness, and an actionable next step.

The endpoint is read-only Enterprise Architecture authority. pg-erd-cloud,
Semantic Data Portal, and LineageWeave evidence remains foreign authority and
is reached only through the already governed receipt/canonical-reference
projection; the API performs no cross-service application-table SQL and never
promotes inferred evidence to authoritative truth.

## Authorization rules

- Liveness and readiness remain unauthenticated.
- The planner requires one Keyverse RS256 bearer. The service verifies the
  cryptographic signature, exact issuer, service audience, expiration,
  tenant UUID, and an allowed EA read role before any database query.
- Keyverse configuration is fail-closed and names the issuer, same-origin JWKS
  endpoint, service audience, tenant claim, role claim, and allowed read roles.
- The `ea_runtime` database login has no application-table access and no direct
  execute privilege on the underlying target-state projector. It receives only
  the purpose-bound `read_technology_target_state_plan(...)` query function.
- The database wrapper binds the already verified tenant UUID transactionally
  before the tenant-scoped projector executes.
- Future mutating requests require tenant, actor, purpose, idempotency, human
  review where applicable, and immutable audit/outbox evidence; this read API
  does not imply a command surface.

## Command rules

- Commands use canonical UUIDv7-backed asset references.
- An inferred proposal and an authoritative command are separate operations.
- Mutations must never be inferred from this read endpoint or from LLM output.

## Error contract

Planner errors expose stable `error_code` and `next_action` fields for missing
or invalid authorization, malformed bitemporal requests, forbidden roles, or an
unavailable purpose-bound query port. Internal SQL, token, credential, and
connector details never appear in responses.
