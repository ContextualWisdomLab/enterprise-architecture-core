# ADR 0020: Preserve exact data-management assessment profile versions

- **Status:** Accepted for active PR #27; not protected-main shipped truth.
- **Scope:** Enterprise Architecture Core inbound projection only.
- **Dependency:** `ContextualWisdomLab/context-graph-contracts#14` remains a provisional read-only contract dependency until an immutable release is available.

## Context

Enterprise Architecture Core consumes assessment results owned by the Data/AI Context system of record and may turn a missing-evidence finding into proposed EA remediation work. The Context Graph assessment grammar identifies both a `profile_code` and an exact `profile_version`. Persisting only the profile code would make historical scores and gap meaning depend on whichever profile definition happens to be current later.

The EA store must preserve source identity, truth origin, evidence provenance, valid/system time, and the exact assessment profile version without copying the foreign assessment store or promoting projected evidence to authoritative EA truth.

## Decision

1. `data_management_assessment_projection` stores an immutable, non-null `profile_version` matching the provider-neutral version grammar used by the Context Graph assessment contract.
2. `record_data_management_assessment_result(...)` requires `profile_version` explicitly. The prior overload without a profile version fails closed rather than inventing or deriving a value from framework version, receipt schema version, or current catalog state.
3. New projection insertion transports the validated version through an internal transaction-local database context used only by the revoked internal writer and its `BEFORE INSERT` guard. Direct service-to-service application-table SQL remains unsupported.
4. Exact replay of an existing assessment result must present the same `profile_version`; a changed version under the same result identity is semantic drift and is rejected.
5. The profile version is immutable after insertion. Superseding assessments append new projection facts and may carry a different exact profile version while preserving the predecessor row unchanged.
6. Because this assessment-projection migration chain has not shipped from a protected release, migration 0035 refuses to fabricate a profile version if pre-existing unreleased projection rows are found.

## Consequences

Historical assessment interpretation remains reproducible even when a profile code is reused for a later definition. The EA Decision Plane still owns only the local projection and proposed remediation decision; Semantic Data Portal remains assessment authority, and Context Graph Contracts remains the provider-neutral interoperability contract.

Repository validation now counts columns introduced through `ALTER TABLE ... ADD COLUMN`, so static schema inventory cannot silently under-report the production PostgreSQL shape.

## Verification trace

- RED PostgreSQL acceptance: `database/tests/zzzzzzzzzzzzzzzzzzzz_verify_data_management_profile_version.sql`.
- Contract-shape and authority fixtures pass an explicit profile version.
- Replay acceptance rejects profile-version drift and the legacy omission overload.
- Migration validator regression: `tests/test_migration_alter_inventory.py`.
- Exact-head CI must pass PostgreSQL clean install, prior-boundary upgrade rehearsal, migration ledger checks, executable invariants, Python validation, package smoke, runtime readiness, and supply-chain gates before this change can be treated as verified.
