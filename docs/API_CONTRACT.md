# API Contract

The implemented OpenAPI contract is in `contracts/openapi.json`; implemented outbound event channels are in `contracts/asyncapi.json`.

Start the `ea-core` process, call `GET /health`, then call `GET /ready`. Use the 503 payload fields to repair the failing dependency before sending tenant traffic.

## Implemented decision surface

`GET /v1/technology-target-state-plans/{technology_version_id}` is the buyer-facing authenticated read. Supply explicit `valid_at` and `recorded_at` CWL timestamps and, optionally, `planning_horizon_days` from 1 through 3650. The response preserves lifecycle impact, affected application/capability, receipt-backed foreign evidence, remediation initiative, target scenario, transformation state, decision readiness, and an actionable next step.

`POST /v1/architecture-transformations/{architecture_transformation_id}/approval` is the human-authorized approval boundary for planner decisions whose next action is `approve_target_state`. Its strict JSON body contains `decision_request_id`, `effective_at`, `decision_reason_text`, and `evidence_record_id`. Transformation, decision-request, and evidence identifiers are canonical UUIDv7. The caller cannot supply an actor: EA Core derives it from the verified Keyverse identity. The command appends authoritative transformation history and `org.contextualwisdomlab.ea.transformation.approved.v1` transactional outbox evidence atomically. Exact decision-request replay is idempotent; conflicting reuse fails closed. A successful receipt directs the caller to `schedule_transformation`.

`POST /v1/architecture-transformations/{architecture_transformation_id}/schedule` is a separate scheduling authority boundary. Its strict body adds canonical UUIDv7 `initiative_milestone_id`. It can bind only the current approved authoritative transformation to an active authoritative milestone belonging to the same remediation initiative. The milestone remains the target-date source of truth, so this command does not create project/task execution state. The command appends an authoritative schedule record and `org.contextualwisdomlab.ea.transformation.scheduled.v1` outbox evidence atomically; a successful receipt directs the caller to `start_transformation`.

`POST /v1/architecture-transformations/{architecture_transformation_id}/start` is a separate execution-state boundary. Its strict body contains `decision_request_id`, `effective_at`, `decision_reason_text`, and `evidence_record_id`. It can advance only the current authoritative transformation that has an accepted schedule. EA Core appends authoritative `started` transformation history and `org.contextualwisdomlab.ea.transformation.started.v1` outbox evidence atomically. The receipt directs the caller to `monitor_transformation`.

`POST /v1/architecture-transformations/{architecture_transformation_id}/complete` is a separate completion boundary. Its strict body contains `decision_request_id`, `effective_at`, `decision_reason_text`, and `evidence_record_id`. It can advance only the current authoritative started transformation. EA Core appends authoritative `completed` history and `org.contextualwisdomlab.ea.transformation.completed.v1` outbox evidence atomically. Completion is intentionally non-final: the receipt directs the caller to `verify_target_state`.

`POST /v1/architecture-transformations/{architecture_transformation_id}/verification` is the evidence-backed target-state verification boundary. Its strict body contains `decision_request_id`, `effective_at`, `decision_reason_text`, `evidence_record_id`, and `verification_outcome_code`. The outcome is exactly `verified` or `gap_detected`. The first verification applies to a current authoritative completed transformation; after a `verified` observation, a later human-authorized decision may append another `verified` or `gap_detected` observation when monitoring has collected newer evidence. Existing history is never rewritten and execution is never reopened. `gap_detected` remains terminal for that transformation and requires replanning. EA Core appends the authoritative verification observation and `org.contextualwisdomlab.ea.transformation.verification_recorded.v1` outbox evidence atomically. `verified` directs the buyer to `monitor_target_state`; `gap_detected` directs the buyer to `replan_target_state`. Verification cannot silently manufacture target-state success from planner, inferred, or LLM output.

`GET /v1/architecture-transformations/{architecture_transformation_id}/monitoring` is the read-only post-verification monitoring boundary. Supply explicit `valid_at` and `recorded_at` CWL timestamps and, optionally, `max_evidence_age_days` from 1 through 3650; the default is 90. The purpose-bound PostgreSQL read returns the exact verification evidence UUID, valid/system timestamps, evidence age, monitoring state, and buyer next action. `current` directs `continue_monitoring`, `stale` directs `collect_new_target_state_evidence`, and `gap_detected` directs `replan_target_state`. Monitoring itself never mutates authoritative history: after `stale`, the buyer collects new evidence and uses the verification command for a new human-authorized observation. Monitoring never promotes inferred, proposed, stale, or foreign evidence to authoritative success.

All mutation commands use UUIDv7 decision/evidence/transformation identities, explicit business-effective time, bounded human reason, actor derivation from verified identity, exact idempotency-key receipt binding, and fail-closed conflicting replay. Outbound events omit the private decision actor and reason.

The read and command surfaces remain Enterprise Architecture authority. pg-erd-cloud physical-schema evidence, Semantic Data Portal Data/AI Context, and LineageWeave inferred/proposed lineage remain foreign authority reached only through governed receipt/canonical-reference projection. No API performs cross-service application-table SQL or promotes foreign inferred evidence to authoritative truth.

## Authorization rules

- Liveness and readiness remain unauthenticated.
- Every `/v1/` decision endpoint requires one Keyverse RS256 bearer. The service verifies signature, exact issuer, service audience, expiration, tenant UUID, and an operation-specific allowed role before database access.
- Planner reads use `EA_READ_ROLES`.
- Approval uses `EA_APPROVAL_ROLES`.
- Scheduling uses `EA_SCHEDULE_ROLES`.
- Starting uses `EA_START_ROLES`.
- Completion uses `EA_COMPLETE_ROLES`.
- Target-state verification uses `EA_VERIFY_ROLES`.
- Post-verification monitoring uses `EA_MONITOR_ROLES`.
- Mutation and monitoring roles are purpose-bound and do not inherit authority from read or sibling roles.
- Keyverse configuration is fail-closed and includes `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, `EA_ROLE_CLAIM`, and every operation-specific role allow-list above.
- JWKS retrieval remains HTTPS, same-origin, redirect-denied, bounded, timeout-limited, and fail-closed.
- No authorization decision is delegated to LLM output or a foreign evidence projection.

## PostgreSQL authority boundary

The `ea_runtime` login has no direct application-table authority. After service-side verification it receives only purpose-bound functions required by the implemented surface:

- `read_technology_target_state_plan(...)`
- `approve_target_state(...)`
- `schedule_transformation(...)`
- `start_scheduled_transformation(...)`
- `complete_started_transformation(...)`
- `record_target_state_verification(...)`
- `read_target_state_monitoring_status(...)`

Each wrapper transaction-locally binds the already verified tenant UUID before tenant-scoped work. The runtime role is not granted direct access to the underlying projectors or foreign-product stores.

## Command and evidence rules

- An inferred/proposed target state, authoritative approval, schedule binding, started execution state, completion record, verification observation, and monitoring decision are distinct states and operations.
- Scheduling binds an existing remediation milestone; it does not duplicate project/task management truth.
- Completion never means verification. A separate evidence-backed human verification is required before the target state can be recorded as verified.
- A stale monitoring result is not a mutation. After new evidence is collected, the same purpose-bound verification command may append a later `verified` or `gap_detected` observation following `verified`; prior history remains immutable and `gap_detected` does not reopen.
- Monitoring is read-only and uses explicit bitemporal cutoffs plus a bounded freshness policy; it cannot mutate authoritative history.
- Human actor, reason, evidence identity, valid time, and system-recorded time remain auditable in authoritative history; privacy-minimized events carry only consumer-required references.
- Authoritative history and transactional outbox evidence commit atomically. A failed command cannot leave one without the other.
- Exact retries return the immutable receipt; decision-request reuse with different meaning fails closed.
- Mutations are never inferred from planner or LLM output.

## Error contract

Planner, approval, scheduling, start, completion, verification, and monitoring errors expose stable `error_code` and `next_action` fields for missing or invalid authorization, malformed requests, forbidden roles, unavailable purpose-bound ports, or command/query failure. Internal SQL, token, credential, actor/reason, and connector details never appear in error responses.
