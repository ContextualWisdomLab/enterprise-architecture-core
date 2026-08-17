# ADR 0018: Joined technology target-state decision projection

- **Status:** Accepted
- **Date:** 2026-08-17
- **Shipping state:** Accepted on this feature branch; not protected-main shipped truth until the owning PR integrates.
- **Depends on:** ADR 0008 (delta scenarios), ADR 0014 (strategy execution), ADR 0015 (bitemporal transformation history), ADR 0016 (bitemporal technology impact), ADR 0017 (receipt-bound cross-domain impact).

## Context

The Enterprise Architecture Decision Plane already records the pieces required to decide what to do about a technology lifecycle change, but they remain exposed through separate governed projections: technology lifecycle impact identifies affected applications and capabilities; receipt-bound cross-domain evidence identifies physical-schema and Data/AI dependencies without copying their owning products; remediation initiatives and immutable-baseline scenarios encode the intended target state; append-only transformation history records execution state.

A buyer should not have to reconstruct those boundaries with ad hoc SQL or copy foreign catalog/schema state merely to answer a bounded decision question. The missing product slice is a deterministic read projection that joins existing authoritative EA facts and receipt-backed foreign references into one next-action surface while preserving every source's authority, truth status, valid time, and system recording time.

ISO/IEC/IEEE 42010:2022 remains the current architecture-description baseline for representing and relating architecture concepts and decisions. W3C PROV-O remains the W3C Recommendation used by this repository for provenance discipline. PostgreSQL 18 remains the runtime baseline for the temporal/RLS enforcement underneath the constituent facts. This ADR introduces no replacement authority model and no new foreign write path.

## Decision

Migration `0020_technology_target_state_plan.sql` adds the read-only function `architecture_core.project_technology_target_state_plan(uuid,timestamptz,timestamptz,integer)`.

The projector starts from `project_technology_change_impact` and, for each impacted application/capability path, joins:

1. receipt-backed external evidence visible through `project_application_context_impact` at the same explicit valid/system cutoffs;
2. an active tenant-owned `architecture_transformation` whose governed scenario currently includes the impacted application through `project_scenario_objects`;
3. the transformation's `remediation_initiative` and immutable-baseline `architecture_scenario` identities; and
4. bitemporal execution state from `project_transformation_state`.

It does **not** insert, update, approve, execute, or otherwise mutate any initiative, scenario, transformation, external reference, receipt, catalog record, physical-schema fact, or lineage fact. It does not query another product's application tables. pg-erd-cloud, Semantic Data Portal, and LineageWeave authority remains represented only by the already-governed canonical external reference plus receipt/truth evidence from ADR 0017.

The function fails closed when the technology identifier, valid-time cutoff, system-recording cutoff, or planning horizon is missing, and it keeps the existing bounded 1..3650-day technology planning horizon.

For each joined path it returns deterministic decision readiness and next-action codes rather than free-form recommendations. The principal transitions are:

- incomplete technology evidence -> preserve the technology projector's evidence-completion/truth-review action;
- missing cross-domain evidence -> `cross_domain_evidence_missing` / `collect_cross_domain_evidence`;
- non-authoritative external evidence -> `truth_review_required` / `review_truth_origin`;
- no governed transformation path -> `remediation_unplanned` / `create_remediation_initiative`;
- proposed transformation -> `target_state_pending_approval` / `approve_target_state`;
- approved transformation -> `approved_not_started` / `schedule_transformation`;
- started transformation -> `execution_in_progress` / `monitor_transformation`;
- completed transformation -> `completed` / `verify_target_state`;
- cancelled/rejected transformation -> `plan_blocked` / `replan_target_state`.

The output deliberately keeps the technology, application, capability, external-reference kind/truth, remediation initiative, scenario, transformation, and transformation-state identities visible so the buyer can inspect the evidence behind the recommended action instead of receiving an opaque score.

## Product boundary

Enterprise Architecture Core owns this decision projection because it joins EA-owned architecture, remediation, target-state, and transformation facts. It does not become a physical-schema store, Data/AI catalog, semantic-lineage engine, workflow engine, or generalized runtime graph.

Foreign systems remain authoritative for their own objects. Receipt-backed references are evidence inputs, not replicated ownership. Inferred/proposed evidence cannot silently become authoritative by appearing in this joined view. The projector is deterministic SQL; no LLM is required for architecture/catalog logic that can be expressed from governed facts.

## Consequences

- A technology lifecycle/EOL review can reach an explicit buyer action without ad hoc cross-product SQL.
- The decision remains reproducible at explicit valid/system cutoffs for the technology impact, cross-domain receipt evidence, and transformation history used by the projection.
- Missing or non-authoritative evidence remains visible as a blocker rather than being converted into a false target-state recommendation.
- The transformation lifecycle itself determines whether the buyer should approve, schedule, monitor, replan, or verify the target state.
- The projection remains a bounded read model. Creation/approval/execution commands continue to use their owning authoritative write paths and human-review policy.

## Verification

`database/tests/zz_verify_z_target_state_planner.sql` is the executable buyer acceptance. It binds an already impacted application into an existing governed target-state scenario, adds receipt-backed physical-schema evidence, and requires the joined projector to return:

- `approve_target_state` while the transformation is proposed;
- `monitor_transformation` after execution has started;
- `verify_target_state` after completion;
- preserved lifecycle classification and external truth/evidence state at each step;
- fail-closed behavior for a missing temporal cutoff; and
- tenant denial when another tenant attempts the same technology projection.

The CI previous-boundary rehearsal must prove migration 0020 upgrades a database containing migrations 0001-0019 and that the new projector exists after that upgrade. Migration-ledger verification derives its expected count from the canonical migration inventory so adding a legitimate contiguous migration cannot leave a stale hard-coded gate.

The feature is not merge-ready until the exact current PR head passes Python 3.11-3.14 validation/coverage, PostgreSQL 18.4 clean-install and previous-boundary upgrade, all SQL acceptance, runtime RLS, package, supply-chain, and applicable review/security gates together.
