# Threat Model

## Scope and status

This threat model covers the Enterprise Architecture Core foundation implemented on the current active foundation branch: the HTTP liveness/readiness surface, PostgreSQL architecture write model and migrations, transactional outbox/projection receipt records, evidence and canonical Context Graph identifiers, and the documented Keyverse identity boundary. Domain command/query endpoints and buyer-facing graph/scenario UI are not yet implemented; the controls below distinguish current database/runtime enforcement from requirements that must be satisfied before those surfaces ship.

The service is an authoritative Enterprise Architecture Decision Plane. It must not accept inferred or proposed cross-product evidence as authoritative merely because a caller can construct a syntactically valid payload.

## Protected assets

- tenant-separated architecture inventory and bitemporal revision history;
- business capability, application, interface, technology and lifecycle facts;
- evidence references and truth-status provenance;
- transformation/scenario decisions when those capabilities are implemented;
- transactional outbox and projection-receipt history;
- Keyverse-derived actor, tenant, role and purpose context once command/query APIs are enabled;
- database credentials, TLS material and connector credentials supplied by deployment infrastructure.

## Trust boundaries

1. **Caller to service.** Future domain APIs must authenticate and authorize before an architecture mutation or protected query. `GET /health` is process-only and `GET /ready` proves dependency state; neither grants tenant authority.
2. **Keyverse to service.** Keyverse is the identity provider boundary. Tokens are untrusted input until signature, issuer, audience, expiry, tenant and role claims are verified for the requested purpose.
3. **Service to PostgreSQL.** The runtime database role is deliberately not general application-table authority. Migrations, forced RLS, composite tenant keys, temporal exclusions and database integrity constraints are defense-in-depth, not a substitute for purpose-bound service authorization.
4. **External evidence/event producer to EA Core.** Canonical CWL identifiers, tenant binding, truth origin, payload shape and replay/idempotency semantics must be validated before an assertion influences authoritative state.
5. **EA Core to downstream projections.** Transactional outbox publication and projection receipts preserve commit ordering and provenance. A projection must not become a second authoritative write model.
6. **Connector/egress boundary.** External calls must use explicit destination policy and bounded resources; credentials, DSNs, tokens and unnecessary raw PII must not enter Context Graph event bundles.

## Threats and required controls

| Threat | Current or required control | Acceptance evidence |
| --- | --- | --- |
| Cross-tenant read/write | Composite tenant/object foreign keys and forced PostgreSQL RLS are implemented; future service commands must derive tenant context only from verified Keyverse claims. | Real PostgreSQL tenant-isolation and RLS acceptance; future API authorization tests before command/query release. |
| Forged or confused identity | Future command/query surface must validate JWT signature, issuer, audience, expiration, tenant and role/purpose claims and must not trust arbitrary PostgreSQL custom GUC values as authority. | Identity-contract tests and purpose-bound service tests are required before publishing domain mutations. |
| Authoritative fact without provenance | `authoritative` and `observed` revisions/relations require evidence; inferred/proposed facts remain explicitly non-authoritative until governed promotion. | Migration 0008 and PostgreSQL evidence-contract acceptance. |
| Cross-tenant evidence URI | Canonical evidence URI tenant must match the owning tenant while allowing same-tenant cross-product authorities. | Insert/update rejection cases in PostgreSQL evidence tests. |
| Bitemporal/history tampering | Active intervals are non-overlapping where required, system/event chronology is constrained, and historical facts are append-preserving rather than hard-deleted. | Temporal exclusion and migration 0009 chronology acceptance. |
| Outbox split-brain or fake publication | Command-side data and outbox rows must commit atomically; publication timestamps cannot precede recording; replay/idempotency remains explicit. | Transaction rollback, event-state and temporal-order tests. |
| Projection spoofing/replay storm | Projection source/event identity and tenant are validated; consumers must bound replay and traversal work and preserve source event identity. | Projection-receipt database tests; bounded replay/traversal tests before external ingestion is released. |
| Graph/query injection or excessive traversal | No graph/Cypher runtime is shipped in the foundation. Any future graph adapter must use typed parameters, deny raw model-authored query execution, and enforce depth/result/resource limits. | Required negative tests before a graph adapter is enabled. |
| Connector SSRF or credential exfiltration | No unrestricted connector egress is implied by the connector catalog. Future adapters require allowlisted destinations, scheme/redirect/DNS controls, bounded I/O and secret separation. | Connector security acceptance before a network adapter is enabled. |
| Prompt-injection policy mutation | LLM output is proposal data only and cannot directly mutate authoritative EA state or security policy. Deterministic authorization and merge/security gates remain independent of model judgment. | Command-boundary tests requiring explicit authorized promotion for proposed/inferred facts. |
| Readiness false positive | Contract version discovery and PostgreSQL readiness probes fail closed on absent, malformed, unavailable, mismatched or exceptional dependencies. Passwords are kept out of argv and supported libpq security/session semantics are preserved or rejected. | Unit tests plus installed-wheel/real PostgreSQL runtime-readiness workflow. |
| Secret or PII propagation | Events must exclude credentials, passwords, tokens, DSNs and unnecessary raw personal attributes. Accountability identifiers remain available only to authorized purposes rather than being blanket-masked. | Schema/event negative tests and future export/access-log acceptance. |
| Supply-chain substitution | Release artifacts must be built from one exact protected head with required CI/security/package/SBOM/provenance/reproducibility evidence. | Release gate and artifact/source hash verification before publication. |

## Abuse cases that must fail closed

- a tenant-A actor supplies a canonical evidence URI naming tenant B;
- an `authoritative` or `observed` fact omits required provenance;
- an inferred or LLM-proposed relation attempts to become authoritative without an explicit authorized transition;
- an event is published before its outbox record time or a projection claims processing before receipt;
- a readiness probe cannot read package metadata, cannot preserve a supplied libpq connection parameter, times out, or cannot prove the expected database/runtime-role boundary;
- a future graph request supplies raw Cypher, unbounded depth, or model-generated policy changes;
- a future connector follows an unapproved redirect or resolves to an unauthorized destination;
- a future token has a valid signature but the wrong issuer, audience, tenant, role, purpose or expiration state.

## Security invariants for future slices

Technology Change Impact, scenario projection and transformation execution may only be added after their command boundaries preserve tenant isolation, bitemporal history, explicit truth origin, evidence provenance and transactional event publication. Read models may cache or project authoritative facts but cannot silently become write authorities. Cross-domain data from Semantic Data Portal, pg-erd-cloud and LineageWeave enters only through versioned contracts and retains its owning authority and truth origin.

## Review and change rule

Any new external API, connector, graph execution path, authorization mechanism, persistent table family, event type, model-backed proposal flow or release channel must update this threat model and add executable negative acceptance at the same boundary. Security documentation is not evidence of enforcement; the associated source, migration, contract and test must remain the authority for implemented behavior.
