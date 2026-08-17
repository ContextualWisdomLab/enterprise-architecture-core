# Test Strategy

## Foundation tests

- deterministic migration naming, composite tenant-key, and forced-RLS
  validation;
- real PostgreSQL 18.4 clean installation of every ordered migration;
- non-superuser RLS visibility and cross-tenant write denial;
- UUIDv7, canonical URI, typed-extension identity, relation endpoint, JSON
  payload, and projection event identity rejection tests;
- overlapping active identity and lifecycle interval rejection;
- overlapping current authoritative revision and relation rejection while
  overlapping proposed assertions remain reviewable beside authoritative facts;
- transactional outbox rollback verification;
- OpenAPI operation, uniqueness, and Keyverse verification contract checks;
- AsyncAPI channel/message/publisher checks;
- exact ADR-count and repository completeness checks;
- public API docstring coverage.

## Portfolio assessment acceptance

The portfolio-assessment milestone extends the real PostgreSQL boundary rather
than testing SQL as source text. Acceptance must prove:

- migration 0010 clean installation and upgrade from the exact 0001-0009
  predecessor boundary with checksum-ledger continuity;
- normalized framework/version, scale/value, dimension, cycle, and object
  assessment persistence;
- rejection when a score value is from a scale other than the dimension's
  scale;
- rejection when a review cycle belongs to a framework other than the
  dimension's framework derived through its scale;
- evidence-required `authoritative` and `observed` assessment truth;
- exclusion of overlapping current authoritative assessment intervals while an
  inferred competing assertion remains reviewable;
- forced-RLS tenant isolation for assessment facts under the non-superuser
  runtime role.

## Subsequent runtime test requirements

Before the corresponding behaviors may merge, add executable evidence for:

- command/outbox atomicity under concurrent application transactions;
- event replay and duplicate-receipt behavior;
- OIDC signature, issuer, audience, expiry, tenant, and role enforcement;
- scenario determinism and current-state non-mutation;
- depth-bounded technology-impact traversal;
- hostile JSON, Unicode, and oversized payload handling.

Production statement and branch coverage remain 100% and skipped security or
integration tests fail the quality gate.
