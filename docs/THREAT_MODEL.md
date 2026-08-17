# Threat Model

## Scope and status

This threat model covers the current Enterprise Architecture Core branch: health/readiness, the authenticated read-only Technology Change Impact & Target-State Planner API, PostgreSQL write model and migrations, transactional outbox/projection receipts, evidence/canonical Context Graph identifiers, and the Keyverse relying-party boundary. Mutating domain APIs and buyer-facing graph/scenario UI are not yet shipped.

EA Core is the authoritative Enterprise Architecture Decision Plane. It must not accept inferred/proposed cross-product evidence as authoritative merely because a caller can construct syntactically valid input.

## Protected assets

- tenant-separated architecture inventory and bitemporal history;
- lifecycle, portfolio, scenario, transformation and target-state decisions;
- evidence references and truth-status provenance;
- transactional outbox and projection-receipt history;
- Keyverse-derived subject, tenant and role context;
- database credentials, TLS material and connector credentials.

## Trust boundaries

1. **Caller to service.** `/health` and `/ready` are unauthenticated probes. The target-state planner requires a verified Keyverse bearer before tenant evidence is queried.
2. **Keyverse to service.** JWT/JWK bytes are untrusted until signature, issuer, audience, expiration/not-before, subject, tenant and role checks pass. JWKS retrieval is same-origin, no-redirect, bounded and fail-closed.
3. **Service to PostgreSQL.** `ea_runtime` has no application-table or underlying-projector authority. It receives only the purpose-bound planner read wrapper after service-side identity verification.
4. **External evidence producer to EA Core.** Canonical identity, tenant, truth origin, payload and replay semantics are validated before evidence influences authoritative decisions.
5. **EA Core to projections.** Outbox publication and projection receipts preserve commit/provenance semantics; projections are not second write authorities.
6. **Connector/egress boundary.** Destinations and resource use must be explicit; credentials, DSNs, tokens and unnecessary raw PII do not enter Context Fabric bundles.

## Threats and controls

| Threat | Implemented or required control | Acceptance evidence |
|---|---|---|
| Cross-tenant planner read | RS256 Keyverse tenant binding plus purpose-bound DB wrapper setting the verified tenant transaction-locally; forced RLS/composite keys remain defense in depth | `test_target_state_api.py`, `zzzz_verify_target_state_query_port.sql`, PostgreSQL RLS acceptance |
| Forged/confused identity | Exact RS256, `kid`, issuer, audience, integer expiry, optional nbf, subject, tenant UUID and allow-listed role checks | `authorization.py`, `test_authorization_hardening.py`, real signed-token fixture |
| JWKS SSRF/redirect/resource abuse | HTTPS under configured issuer origin/path, no redirects, 3 s timeout, 1 MiB bound, strict JSON, one exact `kid` | hostile JWKS configuration/network/size/JSON/key-selection tests |
| Database authorization bypass | `ea_runtime` has no table privilege and no execute privilege on the underlying projector; only fixed-search-path `SECURITY DEFINER` read wrapper is granted | migration 0021, runtime grant bootstrap, PostgreSQL privilege acceptance |
| DSN/token leakage | libpq environment transport keeps credentials out of argv; API errors expose stable codes/actions only | planner reader and safe-failure tests |
| Authoritative fact without provenance | authoritative/observed facts require evidence; inferred/proposed facts retain non-authoritative truth | migrations and PostgreSQL evidence acceptance |
| History tampering | bitemporal exclusions, append-preserving semantics and immutable accepted receipt evidence | temporal, scenario, transformation and receipt-history acceptance |
| Projection spoofing/replay | source/event/tenant validation and receipt-bound idempotency | projection receipt/replay/source-URI tests |
| Connector SSRF or credential exfiltration | connector catalog grants no unrestricted egress; future network adapters require explicit allowlists and redirect/DNS controls | required before a network adapter ships |
| Prompt-injection policy mutation | LLM output remains proposal evidence; deterministic authorization/security/merge gates do not defer to model judgment | truth-origin and command-boundary regressions |
| Readiness false positive | contract/database probes fail closed and preserve supported libpq security/session semantics | unit + real PostgreSQL runtime-readiness workflow |
| Supply-chain substitution | exact-head package/SBOM evidence and protected release provenance | supply-chain/release gates |

## Abuse cases that fail closed

- missing, malformed, unsigned, incorrectly signed, expired, wrong-issuer/audience/tenant/role bearer;
- JWKS redirect, oversized/ambiguous document, missing or duplicate `kid`, or unsafe issuer/JWKS origin;
- direct `ea_runtime` application-table or target-state-projector access;
- malformed/duplicate/unknown bitemporal planner query parameters or unbounded horizon;
- planner DB failure attempting to expose SQL, DSN or credential detail;
- tenant-A evidence naming tenant B;
- inferred/LLM-proposed facts attempting implicit authoritative promotion;
- unapproved connector redirect or unbounded graph traversal.

## Future slices

Mutating EA commands require separate actor/purpose/reason, idempotency, human-review where applicable, immutable audit/outbox and command-specific authorization acceptance. UI work requires accessible exact-value alternatives and export behavior. Documentation alone is never security evidence; source, migration, contract and executable tests remain authoritative.
