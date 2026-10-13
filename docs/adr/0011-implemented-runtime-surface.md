# ADR 0011: Advertise Only the Implemented Process Surface

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Enterprise Architecture Core ships a stdlib HTTP process that binds
`0.0.0.0:$PORT` and implements `GET /health` plus `GET /ready`. The OpenAPI
document advertises those two operations with JSON schemas. Domain create,
update, and query commands remain unpublished until Keyverse-verified command
handlers exist.

The Python distribution name is `enterprise-architecture-core`. Dependency
resolution uses a committed `uv.lock`, and CI fails when the lock would change.

## Consequence

A buyer can start the process, confirm liveness, and keep an instance out of
the serving pool until contracts and database readiness pass. Generated clients
cannot call placeholder CRUD. Reviewed dependency versions are reproducible.
