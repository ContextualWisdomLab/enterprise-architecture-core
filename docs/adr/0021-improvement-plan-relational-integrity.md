# ADR 0021: Bind improvement milestones to their remediation initiatives

- **Status:** Accepted for active PR #27; not protected-main shipped truth.
- **Date:** 2026-08-20
- **Scope:** Enterprise Architecture Core assessment-improvement decision evidence.

## Context

An assessment improvement plan stores both the remediation initiative chosen for a projected evidence gap and the milestone that closes that gap. Independent foreign keys for those two identifiers prove only that both rows exist in the same tenant. They do not prove that the stored milestone actually belongs to the stored initiative. That permits a structurally valid but semantically impossible plan if corrupted or privileged data bypasses the purpose-bound command path.

The database is the authoritative EA Decision Plane and must preserve this relationship even when application code is bypassed. Tenant isolation alone is therefore insufficient; the initiative/milestone pair is one relational fact.

## Decision

1. `initiative_milestone` exposes a tenant-scoped unique identity including `remediation_initiative_id` in addition to its existing primary key.
2. `assessment_improvement_plan` references `(tenant_record_id, initiative_milestone_id, remediation_initiative_id)` as one composite foreign key.
3. The purpose-bound command continues to create the initiative and its milestone atomically, but correctness no longer depends on that command being the only writer capable of preserving the pair.
4. No foreign Data/AI Context authority is copied or mutated; this constraint protects only EA-owned proposed remediation evidence.

## Consequences

A milestone from another initiative fails closed with a PostgreSQL foreign-key violation even if every referenced tenant/object identity exists independently. The constraint also makes replay and later evidence-acceptance slices safe to join the plan to one unambiguous initiative/milestone pair.

## Verification trace

- RED executable PostgreSQL acceptance: `database/tests/zzzzzzzzzzzzzz_verify_improvement_plan_milestone_pair.sql` attempts a cross-initiative milestone insertion.
- GREEN migration: `database/migrations/0036_improvement_plan_pair_integrity.sql` replaces the independent milestone foreign key with the composite pair constraint.
- Repository schema inventory must report the additional live relational constraint.
- Exact-current-head PostgreSQL clean-install and previous-boundary upgrade rehearsals must pass before the change is treated as verified.
