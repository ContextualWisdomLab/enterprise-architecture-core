# Changelog

## [Unreleased]

### Added

- Installable `enterprise-architecture-core` process with `GET /health` and
  `GET /ready` on `0.0.0.0:$PORT`.
- Committed `uv.lock` and CI lock-check so reviewed dependencies cannot drift.
- Ecosystem connector catalog for Keyverse, context-graph-contracts, Semantic
  Data Portal, pg-erd-cloud, LineageWeave, naruon, and organization `.github`.
- Enterprise Architecture Decision Plane product and responsibility baseline.
- PostgreSQL 3NF schema for capabilities, applications, technologies,
  interfaces, temporal relations, lifecycle, evidence, OIDC identity links, and
  transactional outbox events.
- Composite tenant foreign keys and forced PostgreSQL row-level-security
  policies across all tenant-owned tables.
- Database-enforced UUIDv7 identity and canonical asset URI consistency.
- Governed relation endpoint types and non-overlapping active intervals for
  identity links, object revisions, architecture relations, and lifecycle.
- Real PostgreSQL acceptance for RLS, tenant isolation, temporal exclusion,
  typed relations, payload shape, projection identity, and outbox rollback.
- OpenAPI and AsyncAPI contract baselines.
- Keyverse OIDC, tenant-isolation, provenance, and append-preserving history
  requirements.
- Ten accepted ADRs, doctoring references, test strategy, and operability plan.
