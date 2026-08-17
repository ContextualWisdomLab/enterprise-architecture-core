# API Contract

The implemented OpenAPI contract is in `contracts/openapi.json`; implemented outbound event channels are in `contracts/asyncapi.json`.

Start the `ea-core` process, call `GET /health`, then call `GET /ready`. Use the 503 payload fields to repair the failing dependency before sending tenant traffic.

## Implemented decision surface

`GET /v1/technology-target-state-plans/{technology_version_id}` is the buyer-facing authenticated read. Supply explicit `valid_at` and `recorded_at` RFC 3339 timestamps and, optionally, `planning_horizon_days` from 1 through 3650. The response preserves lifecycle impact, affected application/capability, receipt-backed foreign evidence, remediation initiative, target scenario, transformation state, decision readiness, and an actionable next step.

`POST /v1/architecture-transformations/{architecture_transformation_id}/approval` is a separate human-authorized mutation boundary for planner decisions whose next action is `approve_target_state`. Its strict JSON body contains only `decision_request_id`, `effective_at`, `decision_reason_text`, and `evidence_record_id`. The transformation, decision request, and evidence identifiers are UUIDv7. The caller cannot provide an actor: EA Core derives it from the verified Keyverse issuer and subject.

The approval command appends authoritative transformation history and the `org.contextualwisdomlab.ea.transformation.approved.v1` transactional outbox event in one PostgreSQL transaction. The decision request is the idempotency key. An exact replay returns the original immutable receipt; reuse with different command meaning fails closed. The runtime also rejects a database receipt whose returned decision request does not match the exact command key.

The read and command surfaces remain Enterprise Architecture authority. pg-erd-cloud, Semantic Data Portal, and LineageWeave evidence remains foreign authority and is reached only through governed receipt/canonical-reference projection; neither API performs cross-service application-table SQL or promotes inferred evidence to authoritative truth.

## Authorization rules

- Liveness and readiness remain unauthenticated.
- Both decision endpoints require one Keyverse RS256 bearer. The service verifies the cryptographic signature, exact issuer, service audience, expiration, tenant UUID, and an operation-specific allowed role before database access.
- Planner reads use `EA_READ_ROLES`; target-state approval uses the separate `EA_APPROVAL_ROLES` allow-list. Approval authority is not inherited from read authority.
- Keyverse configuration is fail-closed and names the issuer, same-origin JWKS endpoint, service audience, tenant claim, role claim, read roles, and approval roles.
- The `ea_runtime` database login has no direct application-table access. It receives only the purpose-bound `read_technology_target_state_plan(...)` and `approve_target_state(...)` wrappers.
- Each database wrapper transaction-locally binds the already verified tenant UUID before tenant-scoped work executes.
- No authorization decision is delegated to LLM output or to a foreign evidence projection.

## Command rules

- Commands use UUIDv7 decision/evidence/transformation identifiers and explicit effective time.
- An inferred proposal and an authoritative approval are separate operations.
- Human actor and decision reason are retained in immutable history; the outbound event omits those private fields and carries only the references required by consumers.
- History and outbox evidence commit atomically. A failed command cannot leave one without the other.
- Mutations are never inferred from planner output or LLM output.

## Error contract

Planner and approval errors expose stable `error_code` and `next_action` fields for missing or invalid authorization, malformed requests, forbidden roles, unavailable purpose-bound ports, or command failure. Internal SQL, token, credential, actor/reason, and connector details never appear in error responses.
