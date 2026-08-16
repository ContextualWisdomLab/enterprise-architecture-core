# Test Strategy

## Foundation tests

- deterministic migration naming, composite tenant-key, and forced-RLS
  validation;
- OpenAPI operation, uniqueness, and Keyverse verification contract checks;
- AsyncAPI channel/message/publisher checks;
- exact ADR-count and repository completeness checks;
- public API docstring coverage.

## Runtime test requirements

Before runtime code may merge, add:

- real PostgreSQL clean-install and upgrade rehearsal;
- tenant-isolation and cross-tenant foreign-key tests;
- bitemporal overlap and historical-cutoff tests;
- command/outbox atomicity tests;
- event replay and duplicate-receipt tests;
- OIDC signature, issuer, audience, expiry, tenant, and role tests;
- scenario determinism and non-mutation tests;
- depth-bounded impact traversal tests;
- hostile JSON, Unicode, and oversized payload tests.

Production statement and branch coverage remain 100% and skipped security or
integration tests fail the quality gate.
