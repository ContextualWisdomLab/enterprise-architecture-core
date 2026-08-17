# ADR 0016: Bitemporal technology change impact projection

- **Status:** Accepted
- **Date:** 2026-08-17
- **Shipping state:** Accepted on this feature branch; not protected-main shipped truth until the owning PR integrates.
- **Depends on:** ADR 0004 (bitemporal history), ADR 0007 (evidence/truth status), ADR 0015 (bitemporal transformation history).

## Context

Enterprise architects need to turn a technology lifecycle change into an explainable decision path rather than a static inventory alert. The first useful path is owned entirely by the Enterprise Architecture Decision Plane: technology version -> technology component -> application -> business capability. The same query must distinguish what was valid in the real world from what the system had actually recorded at the audit cutoff, preserve the truth origin and evidence of every relation and lifecycle decision, and expose missing or non-authoritative mappings instead of silently treating them as actionable architecture truth.

The pre-existing `technology_version.support_end_date` field is current inventory metadata. It has no independent valid-time/system-recording interval, so using it to classify a historical impact query would allow a later metadata edit to rewrite an earlier audit result. The planner therefore treats bitemporal `lifecycle_interval` facts, not that mutable field, as the authoritative decision-time source for lifecycle risk. A future support-policy model may normalize vendor-specific support commitments separately; until then, the planner must not manufacture temporal semantics that the field does not possess.

Cross-domain evidence such as physical database/schema design, catalog/data-product lineage, inferred lineage, dashboards, models, and AI agents belongs to pg-erd-cloud, Semantic Data Portal, LineageWeave, and their respective owners. This repository must therefore produce a stable EA-owned impact boundary that can later receive those products' published event/contract projections without taking over their stores or querying their application tables.

ISO/IEC/IEEE 42010:2022 remains the current published architecture-description standard and covers enterprises, technologies, architecture concepts, and their relationships. PostgreSQL 18 row-level security remains the runtime tenant-isolation mechanism for EA-owned facts, while PostgreSQL timestamp semantics support independent valid-time and recorded-time cutoffs. These standards inform the representation and enforcement boundary; they do not prescribe this product's impact-planning method.

## Decision

Migration `0015_technology_change_impact.sql` adds the tenant-bound, read-only function `project_technology_change_impact(uuid,timestamptz,timestamptz,integer)`.

The projector starts from one tenant-owned `technology_version`, traverses only EA-owned `has_version`, `uses_technology`, and `supports_capability` relations visible at the requested real-world and system-recording cutoffs, and evaluates current plus upcoming risk-bearing lifecycle intervals under the same two-time rule. A relation or lifecycle interval is visible only when it had been recorded by the requested system cutoff and had not yet been superseded at that cutoff; active relations must additionally contain the requested valid time. Rejected and superseded relation truth origins never participate in the active path.

The projection returns identifiers and buyer-readable codes for the technology component, application, and capability, the current lifecycle phase, the next recorded risk-bearing lifecycle transition timestamp, every traversed relation's truth status and evidence identifier, the lifecycle evidence that caused the decision, and three deterministic decision fields:

- `impact_status_code`: `supported`, `lifecycle_change_soon`, `phase_out`, or `end_of_life`.
- `evidence_state_code`: `complete`, `missing_capability_mapping`, `requires_truth_review`, or `missing_lifecycle_evidence`.
- `recommended_action_code`: `monitor`, `plan_target_state`, `start_remediation`, `complete_capability_mapping`, `review_truth_origin`, or `complete_lifecycle_evidence`.

Evidence gaps and non-authoritative dependency paths take precedence over remediation recommendations because a buyer should first know that the decision path is incomplete or still proposed/inferred rather than receive a falsely precise target-state recommendation. Any `has_version`, `uses_technology`, or `supports_capability` relation with `inferred` or `proposed` truth origin routes the row to `requires_truth_review` / `review_truth_origin`; the projector still exposes the original relation truth statuses and never promotes them. `observed` relations remain visible as observed evidence rather than being relabeled authoritative.

An active `end_of_life`/`retired` lifecycle state escalates to remediation once the EA-owned path is complete and not awaiting truth review. Active phase-out or the earliest recorded `phase_out`/`end_of_life`/`retired` transition inside the explicit planning horizon requests target-state planning. The horizon is caller supplied but bounded to 1..3650 days so a malformed request cannot turn the projection into an effectively unbounded policy query.

When a future lifecycle transition drives the risk classification, the returned lifecycle evidence identifier is the evidence for that transition; otherwise it is the evidence for the current lifecycle interval. This prevents the decision action from being separated from the evidence that actually caused it.

The function is `STABLE` and does not mutate authoritative facts, create scenarios, create initiatives, approve transformations, or promote inferred/proposed evidence. Later slices may use this output to create an explicitly reviewed remediation initiative and scenario through existing governed write paths.

## Product boundary

The projection owns only EA facts and EA decisions. It does not ingest or duplicate Semantic Data Portal assets, pg-erd-cloud schemas, LineageWeave inferred lineage, Keyverse identities, naruon workspace state, or contextual-orchestrator proposals. Cross-product enrichment must arrive through published contracts/events with tenant identity, truth origin, provenance, and replay/idempotency semantics. Service-to-service direct application-table SQL remains prohibited.

## Consequences

- A buyer can ask which applications and capabilities are exposed to a recorded technology lifecycle change and receive explicit evidence provenance plus a concrete next action.
- Late-recorded backfills do not rewrite an earlier audit view; the same valid-time question can return different evidence only when the requested recorded-time cutoff changes.
- Editing non-temporal current `technology_version.support_end_date` metadata cannot rewrite the planner's historical lifecycle classification.
- Proposed or inferred dependency paths remain useful for discovery but are routed to explicit truth review instead of becoming remediation authority.
- Missing capability or lifecycle evidence is visible as a decision-blocking state rather than being mistaken for no impact.
- The first slice stays deterministic and does not require an LLM for catalog/architecture logic.
- Cross-domain impact expansion remains additive: physical schema, data product, dashboard/model/agent, and transformation evidence can be projected later without moving another product's source of truth into this database.

## Verification

`database/tests/zz_verify_technology_change_impact.sql` exercises the real PostgreSQL boundary. It proves late-recorded capability evidence is excluded at an earlier system cutoff, the same evidence becomes visible after its recording time, relation and decision evidence identities survive traversal, an upcoming recorded lifecycle transition produces the deterministic target-state action on an authoritative path, a proposed application/capability path is diverted to truth review, mutating the non-temporal support-end metadata cannot change the historical result, end-of-life escalates to remediation, an invalid horizon fails closed, and an unknown technology version cannot cross the active tenant boundary. CI applies migration 0015 on a clean database, rehearses upgrade from migration 0014, verifies the function exists at the upgraded boundary, checks the exact migration ledger count, and then executes all SQL invariants under the repository's database acceptance role.
