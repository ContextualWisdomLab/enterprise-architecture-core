# ADR 0022: Preserve evidence-backed assessment-improvement dependencies

- **Status:** Accepted for active PR #27; not protected-main shipped truth.
- **Date:** 2026-08-20
- **Scope:** Enterprise Architecture Core assessment-improvement decision evidence.
- **Dependency:** The projected assessment remains owned by Semantic Data Portal and is consumed through the provisional Context Graph assessment contract.

## Context

An assessment gap can require other remediation work to complete first. Recording only a proposed initiative and milestone loses that execution dependency and gives a portfolio buyer no durable answer to “what must happen before this remediation can proceed?” A free-form dependency list would also make replay, tenant isolation, provenance, and relational integrity difficult to verify.

Enterprise Architecture Core owns remediation initiatives and their execution relationships. It does not own the source assessment, and a projected assessment or model proposal must not acquire authoritative status merely because it caused proposed EA work.

## Decision

1. The dependency-aware improvement command requires two explicit aligned arrays: prerequisite initiative UUIDv7 identities and one tenant-scoped evidence-record UUIDv7 identity for each prerequisite. Empty arrays mean the decision explicitly has no dependencies; omission is not equivalent to empty.
2. A decision may contain at most 32 prerequisite initiatives. Prerequisite identities are unique, active, same-tenant remediation initiatives and cannot be rejected or superseded.
3. `assessment_improvement_dependency_set` records the explicit dependency-set cardinality, including zero, so exact replay can distinguish dependency-aware decisions from legacy calls made before this contract existed.
4. `assessment_improvement_dependency_relation` stores one normalized prerequisite/evidence pair per plan. Tenant-composite foreign keys bind the plan, prerequisite initiative, and evidence to the same tenant. The relation is immutable after commit.
5. The dependency-aware command serializes on the source assessment projection, delegates creation of the proposed plan, milestone, and transactional-outbox evidence to the existing purpose-bound command, and inserts the normalized dependency set in the same transaction. Any dependency failure rolls back the entire decision.
6. Exact replay must present the identical prerequisite/evidence set. A changed set under the same decision UUID is semantic drift and fails closed.
7. The original 11-argument database function remains as an internal compatibility surface for the unshipped stacked slice, while the new dependency-aware overload is the contract exercised by issue #25 acceptance. Runtime roles receive no blanket function or table access.

## Consequences

Portfolio and target-state work can now preserve why a remediation initiative is blocked and which evidence supports that dependency without embedding foreign assessment prose or duplicating a project-management system. The dependency graph remains bounded, tenant-scoped, replay-safe, and explicitly proposed where the originating remediation is proposed.

The dependency event projection itself is intentionally not widened in this slice: dependency records are authoritative EA decision evidence inside the same transaction, while cross-domain publication can expose a versioned privacy-minimized projection only after the receiving contract is specified.

## Verification trace

- RED/GREEN PostgreSQL buyer acceptance: `database/tests/zzzzzzzzzzzzzzzzzzzzz_verify_data_management_dependencies.sql`.
- Schema implementation and replay guard: `database/migrations/0036_improvement_plan_pair_integrity.sql`.
- Static schema inventory: `tests/test_migration_validation.py`, `tests/test_migration_alter_inventory.py`, and `tests/test_repository_validation.py`.
- Clean-install/upgrade, RLS, package, runtime-readiness, supply-chain, and exact-head repository checks remain required before this decision can be treated as verified or shipped.
