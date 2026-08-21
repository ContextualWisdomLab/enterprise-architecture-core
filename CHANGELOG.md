# Changelog

## [Unreleased]

### Added

- Bitemporal Technology Change Impact & Target-State Planner projection through `project_technology_change_impact(uuid,timestamptz,timestamptz,integer)`, traversing EA-owned technology-version -> component -> application -> capability facts while preserving relation truth origin/provenance and deriving lifecycle risk only from valid/system-time lifecycle evidence.
- Deterministic buyer next-action states for recorded lifecycle risk, incomplete evidence, and non-authoritative dependency paths (`monitor`, `plan_target_state`, `start_remediation`, `complete_capability_mapping`, `complete_lifecycle_evidence`, `review_truth_origin`), with bounded planning horizons; the projector exposes the next risk-bearing lifecycle transition and its evidence, ignores mutable non-temporal support metadata for historical classification, and never turns inferred/proposed relations into actionable authority.
- Relation-aware target-state scenarios through normalized `scenario_relation_delta` and deterministic `project_scenario_relations(uuid)`, preserving typed endpoint semantics, truth/evidence, immutable append history, and explicit endpoint-integrity state without mutating authoritative relations.
- Relation projection composes with final scenario object presence so a requested-present edge with an absent source or target remains auditable but cannot appear active; real PostgreSQL acceptance covers latest-delta precedence, endpoint typing, provenance, RLS, and previous-boundary upgrade from migration 0012 through 0013.
- Immutable target-state scenario baselines plus ordered object-presence deltas and deterministic `project_scenario_objects(uuid)` projection, preserving exact valid-time/system-time baseline cutoffs without mutating authoritative architecture truth.
- Scenario integrity controls for UUIDv7 identity, tenant-bound foreign keys, forced RLS, authoritative/observed evidence, positive non-reusable delta ordering, target-time semantics, immutable baseline/decision meaning, one-time supersession, and hard-delete rejection.
- Real PostgreSQL scenario-projection buyer acceptance and previous-boundary upgrade rehearsal from migration 0011 through migration 0012.
- Versioned strategy execution facts for architecture objectives, remediation initiatives, objective-contribution links, and ordered initiative milestones with UUIDv7 identity, composite tenant foreign keys, forced RLS, valid/system time, explicit truth origin, and tenant-bound provenance.
- Strategy semantic guards that require authoritative/observed evidence, contain initiative-objective links inside referenced valid-time intervals, keep milestone targets inside initiative validity, require positive milestone sequence values, prevent overlapping current authoritative facts, and preserve decision meaning through one-time supersession plus append.
- Real PostgreSQL strategy-execution acceptance with observed RED-before-GREEN evidence and upgrade rehearsal from migration 0010 through migration 0011.
- Normalized versioned portfolio assessment for framework/version, scale/value, dimension, cycle, and object assessment facts with UUIDv7 identifiers, composite tenant foreign keys, forced RLS, valid/system time, truth origin, and provenance-aware assessment history.
- Database semantic guards that reject a score from the wrong dimension scale or a cycle from another framework, require evidence for authoritative and observed assessments, prevent overlapping current authoritative assessment intervals, and allow inferred alternatives to remain reviewable without promotion.
- Real PostgreSQL portfolio-assessment acceptance plus upgrade rehearsal from migrations 0001-0009 through migration 0010.
- Installable `enterprise-architecture-core` process with process-only `GET /health` and fail-closed dependency-aware `GET /ready` on `0.0.0.0:$PORT`.
- Exact installed Context Graph contract-version readiness and PostgreSQL runtime-role readiness probes; database readiness keeps inline credentials out of argv, preserves supported libpq TLS/channel-binding/host-selection/password-file/passwordless/default-socket/session-target semantics, and rejects unknown or ambiguous query parameters.
- Committed `uv.lock` and CI lock-check so reviewed dependencies cannot drift.
- Exact-head SPDX 3.0.1 SBOM and SHA-256 wheel/sdist evidence on pull requests and protected-main builds, plus protected-main SLSA build-provenance and canonical SPDX 3 SBOM attestations using immutably pinned actions; the same strict bundle verifier exercises generated evidence before upload and re-admits the downloaded wheel/sdist/SPDX/checksum bundle before any protected-main signing, while post-signing verification binds both attestation classes to the exact repository, stable ref, source SHA, signer workflow/digest, GitHub OIDC issuer, hosted-runner policy, artifact bytes, and canonical SPDX meaning.
- Ecosystem connector catalog for Keyverse, context-graph-contracts, Semantic Data Portal, pg-erd-cloud, LineageWeave, naruon, and organization `.github`.
- Enterprise Architecture Decision Plane product and responsibility baseline.
- PostgreSQL 3NF schema for capabilities, applications, technologies, interfaces, temporal relations, lifecycle, evidence, OIDC identity links, and transactional outbox events.
- Composite tenant foreign keys and forced PostgreSQL row-level-security policies across tenant-owned tables.
- Database-enforced UUIDv7 identity, canonical asset URI consistency, typed relation endpoints, provenance integrity, system-time event chronology, payload shape, and non-overlapping active authoritative intervals.
- Real PostgreSQL acceptance for RLS, tenant isolation, temporal exclusion, typed relations, evidence tenant integrity, event chronology, payload shape, projection identity, and outbox rollback.
- Clean-install, idempotent replay, checksum-drift, failed-migration atomicity, and previous-boundary upgrade rehearsal.
- OpenAPI and AsyncAPI contract baselines, Keyverse OIDC boundary requirements, accepted ADRs, doctoring references, standard-to-test traceability, and threat-model distinctions between enforced and planned surfaces.
