# Test Strategy

## Foundation tests

- deterministic migration naming, composite tenant-key, and forced-RLS
  validation;
- real PostgreSQL 18.4 clean installation of every ordered migration;
- non-superuser RLS visibility and cross-tenant write denial;
- UUIDv7, canonical URI, relation endpoint, JSON payload, and projection event
  identity rejection tests;
- overlapping identity, revision, relation, and lifecycle interval rejection;
- transactional outbox rollback verification;
- OpenAPI operation, uniqueness, and Keyverse verification contract checks;
- AsyncAPI channel/message/publisher checks;
- exact ADR-count and repository completeness checks;
- public API docstring coverage.

## Runtime test requirements

Before runtime code may merge, add:

- migration upgrade rehearsal from each released schema version;
- command/outbox atomicity under concurrent application transactions;
- event replay and duplicate-receipt tests;
- OIDC signature, issuer, audience, expiry, tenant, and role tests;
- scenario determinism and non-mutation tests;
- depth-bounded impact traversal tests;
- hostile JSON, Unicode, and oversized payload tests.

Production statement and branch coverage remain 100% and skipped security or
integration tests fail the quality gate.
