# Test Strategy

## Repository-wide gates

- deterministic migration inventory, naming, composite tenant-key, forced-RLS and checksum-ledger validation;
- real PostgreSQL clean install, idempotent replay, previous-boundary upgrade and failed-migration rollback;
- non-superuser RLS visibility and cross-tenant denial;
- UUIDv7, canonical identity, temporal overlap, truth/provenance, projection receipt and outbox invariants;
- OpenAPI/AsyncAPI executable-contract validation;
- Python 3.11-3.14 validation, Ruff, installed wheel/package smoke and exact 100% owned production statement/branch coverage;
- exact-head package/SBOM evidence; skipped applicable required evidence is non-passing.

## Technology Change Impact & Target-State Planner

Real PostgreSQL acceptance proves the bitemporal path from technology lifecycle through affected applications/capabilities, receipt-bound physical-schema/Data-AI evidence, remediation initiative, immutable target scenario and append-preserving transformation state. It verifies deterministic next actions, truth-origin preservation, explicit valid/system cutoffs, bounded horizon, cross-tenant denial and the purpose-bound runtime query port.

## Authenticated planner API

The planner read boundary has executable acceptance rather than a documentation-only OIDC claim:

- a real RS256 fixture verifies cryptographic signature, issuer, service audience, expiration, tenant UUID, role and subject binding;
- negative JWT tests cover wrong algorithm/key/type, invalid signature, wrong issuer/audience, boolean/string expiration, future/invalid nbf, malformed tenant/subject/role and ambiguous audience shapes;
- hostile JWKS tests cover unsafe scheme/origin/path/port/userinfo/query/fragment, redirects, network failure, timeout behavior, response-size bounds, malformed/duplicate/non-standard JSON, missing/duplicate key IDs and invalid RSA key purpose/material;
- every JWS `crit` form is rejected because EA Core implements no critical JWS extensions;
- the HTTP surface proves 401/403/400/503 fail-closed behavior and safe buyer `next_action` copy without leaking token, SQL, DSN or credential material;
- planner request parsing rejects unknown/duplicate parameters, missing bitemporal cutoffs, naive/malformed timestamps and horizons outside 1..3650;
- the service-to-PostgreSQL test proves DSN/password absence from argv and execution only through `read_technology_target_state_plan(...)`;
- real PostgreSQL acceptance proves `ea_runtime` can execute that purpose-bound wrapper but cannot execute the underlying projector or read application tables directly;
- OpenAPI validation binds the exact implemented planner path, Keyverse security, parameter schemas and response/error shapes to executable runtime behavior.

## Governed transformation lifecycle

Each lifecycle mutation is tested independently from planner-read authority and from sibling mutation roles. Planner output is never sufficient authority by itself.

### Approval

- `EA_APPROVAL_ROLES` is a separate allow-list; a read role cannot inherit mutation authority;
- strict HTTP/body parsing covers content type/length bounds, duplicate JSON members, unknown/spoofed actor fields, UUIDv7 decision/evidence/transformation identifiers, offset-aware effective time and bounded human reason;
- service tests derive the actor from verified Keyverse issuer/subject and prove execution only through `approve_target_state(...)`;
- PostgreSQL acceptance proves authoritative/current proposed state, tenant-bound evidence, non-regressing effective time, exact idempotent replay, conflicting replay rejection and rollback;
- authoritative history and `org.contextualwisdomlab.ea.transformation.approved.v1` outbox evidence commit atomically, and the returned receipt must bind to the exact decision request.

### Scheduling

- `EA_SCHEDULE_ROLES` is independent from read/approval roles;
- strict parsing requires canonical decision/evidence/transformation/milestone UUIDv7 identities and bounded reason/effective time;
- PostgreSQL acceptance permits only the current approved authoritative transformation and an active authoritative milestone of the same remediation initiative;
- scheduling never creates or duplicates project/task execution authority;
- schedule binding and `org.contextualwisdomlab.ea.transformation.scheduled.v1` outbox evidence commit atomically, with exact replay and conflicting-replay coverage.

### Start and completion

- `EA_START_ROLES` and `EA_COMPLETE_ROLES` are separate purpose-bound allow-lists;
- start accepts only a currently approved transformation with an accepted schedule; completion accepts only a current authoritative started transformation;
- malformed bodies, spoofed actors, invalid UUIDv7/time/reason/evidence values, forbidden roles and unavailable purpose-bound ports fail closed;
- each command proves exact decision-request idempotency, authoritative append-preserving history, rollback, tenant isolation and atomic privacy-minimized transactional outbox evidence;
- completion explicitly directs `verify_target_state` rather than conflating execution completion with verified target state.

### Target-state verification

- `EA_VERIFY_ROLES` is independent from every preceding role;
- only a current authoritative completed transformation can receive `verified` or `gap_detected` evidence;
- the actor is Keyverse-derived, evidence/time/reason is explicit and canonical, and exact replay/conflicting replay semantics remain enforced;
- `verified` produces `monitor_target_state`; `gap_detected` produces `replan_target_state`;
- real PostgreSQL and runtime tests prove inferred/proposed/planner/LLM evidence cannot silently become authoritative verification success;
- `org.contextualwisdomlab.ea.transformation.verification_recorded.v1` evidence commits atomically with terminal history.

OpenAPI validation binds the exact POST commands, strict request/receipt schemas, stable 200/201/400/401/403/503 responses and their operation-specific role configuration. AsyncAPI validation requires each emitted transformation event to reuse the shared Context Graph CloudEvent envelope. Libpq tests keep credentials out of argv and pin the documented `PGSSLSNI` mapping.

## Post-verification monitoring

The monitoring read is tested as an executable authority and evidence boundary rather than documentation-only freshness logic:

- `EA_MONITOR_ROLES` is separate from planner and every mutation role; missing/forbidden monitoring authority fails closed;
- route parsing requires exactly one canonical transformation UUIDv7, explicit valid/system cutoffs, no unknown/duplicate parameters, and integer `max_evidence_age_days` from 1 through 3650; Python booleans are explicitly rejected as age policy values;
- database-port tests cover missing/invalid DSN, process launch failure, timeout, non-zero `psql`, malformed/non-object JSON and safe error mapping;
- returned evidence must bind to the requested transformation, canonical evidence UUIDv7, valid/system verification timestamps, allowed verification state, non-negative integer evidence age, monitoring state and its exact deterministic next action;
- real PostgreSQL acceptance proves `current`, `stale`, and `gap_detected` behavior at explicit bitemporal cutoffs and verifies `ea_runtime` has execute authority only through `read_target_state_monitoring_status(...)`, not direct application-table access;
- OpenAPI mutation regressions reject monitoring operation-ID, authorization or parameter-set drift; repository contract counts and operator configuration must remain synchronized;
- monitoring is read-only and tests never accept stale/gap/inferred evidence as authoritative current success.

## Data-management assessment reassessment

The assessment-improvement loop is tested at the authoritative PostgreSQL command boundary as well as the authenticated HTTP/runtime port:

- reassessment is available only after every projected missing-evidence gap has accepted evidence and the request binds to the acceptance whose transactional evidence proves it causally closed the final gap; business-time ordering of `accepted_at` cannot substitute for that recorded causation;
- exact decision replay must return the original immutable reassessment-request and transactional-outbox identities, while changed meaning for the same decision or a second decision for the same assessment fails closed;
- concurrent exact replay is exercised with two independent PostgreSQL sessions and an explicitly observed row-lock wait, proving callers serialize before replay-state inspection and converge on one durable request/outbox pair instead of racing unique constraints;
- the serialization lock is tenant-local to the immutable assessment projection and does not make Semantic Data Portal evidence authoritative inside EA Core;
- runtime acceptance preserves separate `EA_DATA_MANAGEMENT_RECHECK_ROLES`, strict UUIDv7/time/body parsing, bounded credential-safe libpq execution, tenant restoration, exact receipt shape, and fail-closed 400/401/403/503 handling.

The separately authorized reassessment-status read is also executable rather than a documentation-only follow-up:

- `EA_DATA_MANAGEMENT_RECHECK_READ_ROLES` is independent from reassessment mutation authority, and `ea_runtime` receives only the purpose-bound `read_data_management_assessment_recheck_status(...)` port;
- with no successor, the read returns `awaiting_result`; `authoritative` or `observed` current evidence may produce ordinary `evidence_gap`/`evidence_complete`, while inferred/proposed/superseded/rejected current evidence remains `review_required`;
- a late-arriving successor whose `knowledge_cutoff_at` predates the governed reassessment request fails closed even when its EA-local system receipt is newer, preserving valid-time knowledge causality independently from system-recording order;
- immutable truth review is exercised by appending a proposed successor and then an observed successor that supersedes it; the status reader must follow the unique linear supersession chain to the reviewed current evidence instead of pinning the buyer to stale `review_required` state;
- the supersession traversal has a fixed 32-projection bound. Real PostgreSQL acceptance constructs a 33-projection chain inside a nested subtransaction, requires the exact depth failure, and proves the synthetic chain rolls back without leaking fixture state;
- tenant context is restored on success and failure, cross-tenant reads fail closed, readiness/missing-evidence consistency is checked on the selected current projection, and the read never mutates Semantic Data Portal or EA history.

## Remaining future requirements

Before corresponding future features merge, add executable evidence for additional command/outbox concurrency races beyond the reassessment boundary, bounded traversal and injection handling for future general-purpose graph surfaces, OpenLineage ingestion/replay storms, cross-domain receipt stress and recovery, and accessible exact-value/export behavior for buyer UI surfaces. Backup/restore and release rehearsal must prove the entire governed lifecycle, terminal verification evidence, monitoring source evidence, and reassessment request/status/outbox state survive restoration consistently.

No source-text assertion substitutes for a real PostgreSQL, HTTP, cryptographic, package or integration boundary when that executable boundary exists.
