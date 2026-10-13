# ADR 0015: Bitemporal transformation execution history

- **Status:** Accepted
- **Date:** 2026-08-17
- **Shipping state:** Accepted on this feature branch; not protected-main shipped truth until the owning PR integrates.
- **Depends on:** ADR 0004 (bitemporal history), ADR 0007 (evidence/truth status), ADR 0008 (delta scenarios), ADR 0014 (versioned strategy execution).

## Context

A target-state scenario and a remediation initiative answer what architecture should change and why, but they do not preserve the governed execution decision that connects an approved target to what actually happened. Treating that history as mutable workflow state would erase prior decisions, conflate project-management responsibility with the Enterprise Architecture Decision Plane, and make valid-time and system-time questions impossible to answer independently.

The Decision Plane needs to answer two different questions without rewriting history: "what state was intended to be effective at this business time?" and "what had the system recorded by this audit cutoff?" A future-effective approval may legitimately be recorded before its effective date, so recorded time must not be constrained to occur after effective time.

## Decision

Migration `0014_transformation_history.sql` introduces two normalized tenant-owned relations:

1. `architecture_transformation` binds one immutable-baseline `architecture_scenario` to one `remediation_initiative`, with an independent valid interval, system recording/supersession interval, truth status, and evidence.
2. `transformation_history_record` is an append-only ordered state history for that transformation. Each row has independent `effective_at` and `recorded_at`, actor, reason, truth status, and evidence.

Allowed state transitions are deliberately narrow: `proposed -> approved|rejected`, `approved -> started|cancelled`, and `started -> completed|cancelled`. Terminal states do not transition. Approval, cancellation, and rejection require authoritative truth. Started and completed states require authoritative or observed truth. Authoritative and observed facts require evidence.

A governed transformation cannot promote a proposed or inferred parent scenario or remediation initiative. An `approved`, `started`, `completed`, or `cancelled` history state additionally requires the transformation itself to be authoritative. This keeps authority changes explicit at each layer instead of allowing a later record to elevate a weaker source fact.

The database does not require `recorded_at >= effective_at`. System recording time and real-world effective time are independent dimensions. Within one transformation stream, sequence numbers are contiguous, effective times do not move backward, and recording times do not move backward, preserving deterministic replay while still allowing a decision to be recorded before its future effective date.

`project_transformation_state(transformation_id, valid_at, recorded_at)` returns the state visible at both requested cutoffs. It is tenant-bound through `current_tenant_id()` and does not promote inferred or proposed evidence into authoritative state.

Transformation meaning is immutable after insertion except for one-time supersession. History rows cannot be updated or deleted. Corrections therefore append or supersede facts instead of rewriting audit history.

## Product boundary

This model is an Enterprise Architecture decision/history surface, not a project or workflow engine. It does not own staffing, tasks, sprints, ticket execution, deployment telemetry, identity authority, physical schema authority, catalog/lineage authority, or orchestration policy. Keyverse remains the identity authority; `decision_actor_ref` is an audit reference rather than an authorization implementation. Cross-product integration must use contracts/events rather than direct application-table SQL.

## Consequences

- Buyers can reconstruct an approved target-state transformation and its later execution state without losing earlier decisions.
- Audit queries can distinguish a future-effective decision already known to the system from a decision not yet recorded at an earlier system-time cutoff.
- Proposed or inferred automation output cannot silently become an authoritative scenario, transformation, or approval.
- RLS and composite tenant foreign keys preserve tenant isolation.
- The next vertical slice can project cross-domain evidence and impact paths onto this governed transformation identity instead of inventing a second execution model.

## Verification

`database/tests/zz_verify_transformation_history.sql` exercises evidence requirements, authority promotion rejection, invalid transition rejection, future-effective/system-time independence, valid-time and system-time projection, append-only history, and runtime tenant isolation against real PostgreSQL. `database/tests/zz_verify_transformation_authority_boundary.sql` proves that proposed parent facts and proposed transformation identities cannot be promoted by later authoritative-looking rows. The CI upgrade rehearsal installs the previous migration boundary and then applies the current migration so this model must work on both clean install and upgrade paths.
