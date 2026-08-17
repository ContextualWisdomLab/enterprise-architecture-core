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
- the HTTP surface proves 401/403/400/503 fail-closed behavior and safe buyer `next_action` copy without leaking token, SQL, DSN or credential material;
- planner request parsing rejects unknown/duplicate parameters, missing bitemporal cutoffs, naive/malformed timestamps and horizons outside 1..3650;
- the service-to-PostgreSQL test proves DSN/password absence from argv and execution only through `read_technology_target_state_plan(...)`;
- real PostgreSQL acceptance proves `ea_runtime` can execute that purpose-bound wrapper but cannot execute the underlying projector or read application tables directly;
- OpenAPI validation binds the exact implemented planner path, Keyverse security, parameter schemas and response/error shapes to executable runtime behavior.

## Governed target-state approval

The mutation boundary is tested independently from read authorization and never treats planner advice as authority by itself:

- approval-role tests prove `EA_APPROVAL_ROLES` is a separate allow-list and that a read role cannot silently inherit mutation authority;
- strict HTTP/body parsing covers content type/length bounds, duplicate JSON members, unknown/spoofed actor fields, UUIDv7 decision/evidence/transformation identifiers, offset-aware effective time and bounded human decision reason;
- service tests derive the decision actor from the verified Keyverse issuer/subject and prove the DSN/password remains out of argv while only `approve_target_state(...)` is called;
- PostgreSQL acceptance proves the transformation must be authoritative and currently proposed, evidence is tenant-bound, effective time cannot move backward, exact decision-request replay is idempotent, conflicting replay is rejected, and failed validation rolls back;
- authoritative transformation history and `org.contextualwisdomlab.ea.transformation.approved.v1` outbox evidence must commit atomically; replay fails if history exists without its event;
- the runtime receipt is bound to the exact decision request so a successful database call cannot acknowledge another idempotency key;
- OpenAPI validation requires the exact POST command, strict request/receipt schemas, stable 200/201/400/401/403/503 responses, and separate approval-role configuration;
- AsyncAPI validation requires the transformation-approved publisher to reuse the shared Context Graph CloudEvent envelope;
- libpq connection-environment coverage pins the documented `PGSSLSNI` mapping for the PostgreSQL `sslsni` parameter.

## Remaining future requirements

Before corresponding future features merge, add executable evidence for broader command/outbox concurrency races, bounded graph traversal/injection handling, OpenLineage ingestion replay storms, additional transformation commands, and accessible exact-value/export behavior for UI surfaces.

No source-text assertion substitutes for a real PostgreSQL, HTTP, cryptographic, package or integration boundary when that executable boundary exists.
