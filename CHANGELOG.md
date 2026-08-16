# Changelog

## [Unreleased]

### Added

- Installable `enterprise-architecture-core` process with process-only
  `GET /health` and fail-closed dependency-aware `GET /ready` on
  `0.0.0.0:$PORT`.
- Exact installed Context Graph contract-version readiness and PostgreSQL
  runtime-role readiness probes; package-metadata discovery exceptions now fail
  closed on the contract dimension instead of terminating the process surface,
  while the database probe keeps inline credentials out of argv, preserves
  supported libpq TLS, channel-binding, host-selection,
  password-file/passwordless authentication, default Unix-socket, and
  target-session connection semantics, and rejects unknown or ambiguous query
  parameters.
- Committed `uv.lock` and CI lock-check so reviewed dependencies cannot drift.
- Exact-head SPDX 3.0.1 SBOM and SHA-256 wheel/sdist evidence on pull requests
  and protected-main builds, plus protected-main SLSA build-provenance and SBOM
  attestations using immutably pinned GitHub/Anchore actions.
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
- Provenance integrity requiring `authoritative` and `observed` object revisions
  and architecture relations to reference evidence, plus database rejection of
  evidence URIs whose embedded CWL tenant differs from the owning row tenant.
- Database-enforced system-time chronology so an outbox event cannot be
  published before it was recorded and a projection receipt cannot be processed
  before it was received.
- Real PostgreSQL acceptance for RLS, tenant isolation, temporal exclusion,
  typed relations, evidence insert/update tenant integrity, event chronology,
  payload shape, projection identity, and outbox rollback.
- Clean-install, idempotent replay, checksum-drift, failed-migration atomicity,
  and previous-boundary upgrade rehearsal through migration 0009.
- OpenAPI and AsyncAPI contract baselines.
- Keyverse OIDC, tenant-isolation, provenance, and append-preserving history
  requirements.
- Accepted ADR and doctoring baseline with executable standard-to-test
  traceability.
- Foundation threat model distinguishing currently enforced runtime/database
  controls from graph, connector, domain-command, model-backed, and UI controls
  that must fail closed before those future surfaces ship.
