# Threat Model

## Scope and status

This threat model covers the current Enterprise Architecture Core branch: health/readiness, the authenticated Technology Change Impact & Target-State Planner read API, the separately authorized human target-state approval command, PostgreSQL write model and migrations, transactional outbox/projection receipts, evidence/canonical Context Graph identifiers, and the Keyverse relying-party boundary. Buyer-facing graph/scenario UI and broader transformation workflow surfaces are not yet shipped.

EA Core is the authoritative Enterprise Architecture Decision Plane. It must not accept inferred/proposed cross-product evidence as authoritative merely because a caller can construct syntactically valid input. Planner advice remains non-mutating until a separately authorized human approval command succeeds.

## Protected assets

- tenant-separated architecture inventory and bitemporal history;
- lifecycle, portfolio, scenario, transformation and target-state decisions;
- evidence references and truth-status provenance;
- immutable human approval actor/reason/history and decision idempotency keys;
- transactional outbox and projection-receipt history;
- Keyverse-derived subject, tenant and operation-specific role context;
- database credentials, TLS material and connector credentials.

## Trust boundaries

1. **Caller to service.** `/health` and `/ready` are unauthenticated probes. Planner reads and target-state approvals require a verified Keyverse bearer before tenant evidence is queried or authoritative history is appended.
2. **Keyverse to service.** JWT/JWK bytes are untrusted until signature, issuer, audience, expiration/not-before, subject, tenant and role checks pass. JWKS retrieval is same-origin, no-redirect, bounded and fail-closed. Planner read roles and approval roles are configured separately.
3. **Service to PostgreSQL.** `ea_runtime` has no application-table or underlying-projector authority. It receives only the purpose-bound planner read wrapper and target-state approval command wrapper after service-side identity verification. Each subprocess drops inherited `PG*` state and reconstructs libpq settings solely from the validated EA database DSN plus the bounded service timeout.
4. **Human approval boundary.** The caller supplies the proposed transformation, UUIDv7 decision request, effective time, bounded decision reason and evidence reference. The actor is derived from the verified Keyverse issuer/subject; caller actor spoofing is not accepted. Exact retries are idempotent, conflicting reuse fails closed, and authoritative history plus outbox evidence commit atomically.
5. **External evidence producer to EA Core.** Canonical identity, tenant, truth origin, payload and replay semantics are validated before evidence influences authoritative decisions.
6. **EA Core to projections.** Outbox publication and projection receipts preserve commit/provenance semantics; projections are not second write authorities. Approval events omit private actor/reason text.
7. **Connector/egress boundary.** Destinations and resource use must be explicit; credentials, DSNs, tokens and unnecessary raw PII do not enter Context Fabric bundles.

## Threats and controls

| Threat | Implemented or required control | Acceptance evidence |
|---|---|---|
| Cross-tenant planner read | RS256 Keyverse tenant binding plus purpose-bound DB wrapper setting the verified tenant transaction-locally; forced RLS/composite keys remain defense in depth | `test_target_state_api.py`, `zzzz_verify_target_state_query_port.sql`, PostgreSQL RLS acceptance |
| Unauthorized target-state mutation | separate `EA_APPROVAL_ROLES`, verified tenant/subject, no caller-supplied actor, UUIDv7 decision/evidence/transformation IDs, purpose-bound command wrapper | `test_target_state_approval_api.py`, migration 0022 PostgreSQL acceptance |
| Duplicate/conflicting approval | decision request is the idempotency key; exact replay returns the original receipt; conflicting meaning is rejected; runtime binds the returned receipt to the exact decision request | approval API/receipt regressions and `zzzzz_verify_target_state_approval.sql` |
| Approval history without event evidence | transformation history and typed outbox event are one PostgreSQL transaction; replay rejects history lacking its event | migration 0022 and rollback/idempotency acceptance |
| Forged/confused identity | Exact RS256, `kid`, issuer, audience, integer expiry, optional nbf, subject, tenant UUID and allow-listed operation role checks | `authorization.py`, `test_authorization_hardening.py`, real signed-token fixture |
| JWKS SSRF/redirect/resource abuse | HTTPS under configured issuer origin/path, no redirects, 3 s timeout, 1 MiB bound, strict JSON, one exact `kid` | hostile JWKS configuration/network/size/JSON/key-selection tests |
| Database authorization bypass | `ea_runtime` has no table privilege or underlying-projector privilege; only fixed-search-path `SECURITY DEFINER` read/command wrappers are granted | migrations 0021/0022, runtime grant bootstrap, PostgreSQL privilege acceptance |
| Ambient libpq authority injection | drop every inherited `PG*` environment variable before applying the allow-listed, non-duplicate DSN connection parameters; preserve only unrelated process environment and a bounded default connection timeout | `test_postgres_environment_isolation.py`, planner/approval database-port and readiness tests |
| DSN/token leakage | libpq environment transport keeps credentials out of argv; API errors expose stable codes/actions only; `sslsni` uses documented `PGSSLSNI` | planner/approval database-port and connection-environment tests |
| Authoritative fact without provenance | authoritative/observed facts require evidence; inferred/proposed facts retain non-authoritative truth | migrations and PostgreSQL evidence acceptance |
| History tampering | bitemporal exclusions, append-preserving semantics and immutable accepted receipt/approval evidence | temporal, scenario, transformation, approval and receipt-history acceptance |
| Projection spoofing/replay | source/event/tenant validation and receipt-bound idempotency | projection receipt/replay/source-URI tests |
| Connector SSRF or credential exfiltration | connector catalog grants no unrestricted egress; future network adapters require explicit allowlists and redirect/DNS controls | required before a network adapter ships |
| Prompt-injection policy mutation | LLM output remains proposal evidence; deterministic authorization/security/merge gates do not defer to model judgment | truth-origin and command-boundary regressions |
| Readiness false positive | contract/database probes fail closed; libpq authority comes from the validated EA DSN rather than ambient `PG*` state | unit + real PostgreSQL runtime-readiness workflow |
| Supply-chain substitution | exact-head package/SBOM evidence and protected release provenance | supply-chain/release gates |

## Abuse cases that fail closed

- missing, malformed, unsigned, incorrectly signed, expired, wrong-issuer/audience/tenant/role bearer;
- a read-only role attempting the approval command or missing approval-role configuration;
- caller-supplied actor fields, non-UUIDv7 approval identifiers, naive/malformed effective time, empty/oversized reason, duplicate JSON members or oversized/non-JSON command bodies;
- reuse of one decision request for different transformation/time/actor/reason/evidence meaning;
- a database receipt acknowledging another decision request;
- approval history lacking its transactional outbox evidence;
- JWKS redirect, oversized/ambiguous document, missing or duplicate `kid`, or unsafe issuer/JWKS origin;
- direct `ea_runtime` application-table or target-state-projector access;
- ambient `PGSERVICE`, `PGSERVICEFILE`, `PGOPTIONS`, connection, TLS, or session settings attempting to alter the reviewed EA database authority;
- malformed/duplicate/unknown bitemporal planner query parameters or unbounded horizon;
- planner/approval DB failure attempting to expose SQL, DSN or credential detail;
- tenant-A evidence naming tenant B;
- inferred/LLM-proposed facts attempting implicit authoritative promotion;
- unapproved connector redirect or unbounded graph traversal.

## Future slices

Additional mutating EA commands require their own actor/purpose/reason, idempotency, human-review where applicable, immutable audit/outbox and command-specific authorization acceptance. UI work requires accessible exact-value alternatives and export behavior. Documentation alone is never security evidence; source, migration, contract and executable tests remain authoritative.
