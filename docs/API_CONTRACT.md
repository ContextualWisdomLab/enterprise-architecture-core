# API Contract

The initial OpenAPI contract is in `contracts/openapi.json`.

Start the `ea-core` process, call `GET /health`, then call `GET /ready`. Use
the 503 payload fields to repair the failing dependency before sending tenant
traffic.

## Command rules

- Bearer authentication is required except for liveness and readiness.
- Every mutating request will require tenant, actor, purpose, and idempotency
  context when runtime endpoints are implemented.
- Commands use canonical UUIDv7-backed asset references.
- An inferred proposal and an authoritative command are separate operations.
- The response returns the authoritative object reference and revision.

## Initial resources

- business capabilities;
- applications;
- technology components;
- application interfaces;
- architecture relations.

## Error contract direction

The runtime will use stable problem-detail codes for invalid contract,
unauthorized purpose, tenant mismatch, stale revision, invalid interval, and
unsupported relation type. Internal SQL, token, and connector details must not
appear in responses.
