# Test Strategy

## Foundation tests

- deterministic migration naming, composite tenant-key, and forced-RLS validation;
- real PostgreSQL 18.4 clean installation of every ordered migration;
- non-superuser RLS visibility and cross-tenant write denial;
- UUIDv7, canonical URI, typed-extension identity, relation endpoint, JSON payload, and projection-event identity rejection;
- overlapping active identity/lifecycle and current authoritative revision/relation rejection while proposed assertions remain reviewable;
- transactional outbox rollback verification;
- OpenAPI operation, uniqueness, and Keyverse verification-contract checks;
- AsyncAPI channel/message/publisher checks;
- exact repository-document/ADR completeness and public API docstrings;
- 100% owned production statement and branch coverage where tooling exposes them.

## Portfolio assessment acceptance

The portfolio-assessment milestone exercises SQL through a real PostgreSQL boundary. Acceptance proves migration 0010 clean installation and upgrade, normalized framework/scale/value/dimension/cycle/object-assessment persistence, scale/framework consistency, evidence-required authoritative/observed truth, exclusion of overlapping current authoritative scores, reviewable inferred alternatives, append-preserving assessment meaning, and forced-RLS tenant isolation.

## Strategy execution acceptance

The strategy-execution milestone follows an observed RED-before-GREEN path on the hosted PostgreSQL job. The initial acceptance required four authoritative strategy tables before migration 0011 existed and failed at that missing-table boundary. The GREEN implementation must then prove on the exact current PR integration head:

- migration 0011 clean installation and upgrade from the exact migration-0010 boundary with checksum-ledger continuity;
- normalized `strategy_objective`, `remediation_initiative`, `initiative_objective_link`, and `initiative_milestone` persistence;
- evidence-required `authoritative` and `observed` objective/initiative/link/milestone truth;
- same-tenant composite foreign keys and forced-RLS denial of cross-tenant strategy writes;
- rejection of initiative-objective link validity outside either referenced valid-time interval;
- rejection of milestone validity or `target_at` outside the parent initiative interval;
- positive milestone sequence numbers and rejection of invalid coded identifiers;
- exclusion of overlapping current authoritative semantic identities while inferred/proposed alternatives remain reviewable;
- semantic immutability after insertion, one-time supersession, and preservation of historical system-recorded meaning;
- unchanged Python 3.11-3.14 validation, package, runtime-readiness, SBOM, and supply-chain evidence on the resulting exact head.

No source-text assertion substitutes for the real PostgreSQL execution boundary when PostgreSQL can enforce the behavior directly.

## Release-package reproducibility

Release evidence includes a dedicated executable reproducibility boundary. On every pull request and `develop`/`main` integration push, the `reproducibility` workflow checks out the exact workflow commit into two independent clean trees, verifies both dependency locks, derives `SOURCE_DATE_EPOCH` from that exact commit, builds wheel and source distribution independently, and fails closed unless both build directories expose the same artifact filenames and byte-identical SHA-256 identities. Symlinked or path-replaced artifacts are rejected through stable regular-file reads. A single successful build or matching package metadata is not reproducibility evidence.

## Subsequent runtime test requirements

Before the corresponding behaviors may merge, add executable evidence for:

- command/outbox atomicity under concurrent application transactions;
- event replay and duplicate-receipt behavior;
- OIDC signature, issuer, audience, expiry, tenant, role, and purpose enforcement;
- immutable-baseline plus ordered-delta scenario determinism and current-state non-mutation;
- transformation execution that closes old intervals and appends new authoritative facts atomically;
- depth-bounded technology-impact traversal;
- hostile JSON, Unicode, oversized payload, replay-storm, and injection handling;
- accessible exact-value alternatives and export behavior when decision UI is introduced.

Skipped required security or integration evidence is non-passing.
