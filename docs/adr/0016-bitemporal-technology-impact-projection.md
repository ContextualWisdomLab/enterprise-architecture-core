# ADR 0016: Bitemporal technology change impact projection

- **Status:** Accepted
- **Date:** 2026-08-17
- **Shipping state:** Accepted on this feature branch; not protected-main shipped truth until the owning PR integrates.
- **Depends on:** ADR 0004 (bitemporal history), ADR 0007 (evidence/truth status), ADR 0015 (bitemporal transformation history).

## Context

Enterprise architects need to turn a technology support or lifecycle change into an explainable decision path rather than a static inventory alert. The first useful path is owned entirely by the Enterprise Architecture Decision Plane: technology version -> technology component -> application -> business capability. The same query must distinguish what was valid in the real world from what the system had actually recorded at the audit cutoff, preserve the truth origin and evidence of every relation, and expose missing mappings instead of silently treating them as no impact.

Cross-domain evidence such as physical database/schema design, catalog/data-product lineage, inferred lineage, dashboards, models, and AI agents belongs to pg-erd-cloud, Semantic Data Portal, LineageWeave, and their respective owners. This repository must therefore produce a stable EA-owned impact boundary that can later receive those products' published event/contract projections without taking over their stores or querying their application tables.

ISO/IEC/IEEE 42010:2022 remains the current published architecture-description standard and explicitly covers enterprises, technologies, architecture concepts, and their relationships. PostgreSQL 18 row-level security remains the runtime tenant-isolation mechanism for EA-owned facts, while PostgreSQL timestamp/date semantics support independent valid-time and recorded-time cutoffs. These standards inform the representation and enforcement boundary; they do not prescribe this product's impact-planning method.

## Decision

Migration `0015_technology_change_impact.sql` adds the tenant-bound, read-only function `project_technology_change_impact(uuid,timestamptz,timestamptz,integer)`.

The projector starts from one tenant-owned `technology_version`, traverses only currently visible EA-owned `has_version`, `uses_technology`, and `supports_capability` relations, and evaluates lifecycle evidence at the requested real-world and system-recording cutoffs. A relation is visible only when its valid interval contains the requested valid time, it had been recorded by the requested system cutoff, and it had not yet been superseded at that cutoff. Rejected and superseded truth origins never participate in the active path.

The projection returns identifiers and buyer-readable codes for the technology component, application, and capability, the version's support-end date and lifecycle phase, every traversed relation's truth status and evidence identifier, the lifecycle evidence identifier, and three deterministic decision fields:

- `impact_status_code`: `supported`, `support_ending_soon`, `phase_out`, `unsupported`, or `end_of_life`.
- `evidence_state_code`: `complete`, `missing_capability_mapping`, or `missing_support_evidence`.
- `recommended_action_code`: `monitor`, `plan_target_state`, `start_remediation`, `complete_capability_mapping`, or `complete_support_evidence`.

Evidence gaps take precedence over remediation recommendations because a buyer should first know that the decision path is incomplete rather than receive a falsely precise target-state recommendation. End-of-life or already unsupported technology escalates to remediation once the EA-owned path is complete. Phase-out or support ending inside the explicit planning horizon requests target-state planning. The horizon is caller supplied but bounded to 1..3650 days so a malformed request cannot turn the projection into an effectively unbounded policy query.

The function is `STABLE` and does not mutate authoritative facts, create scenarios, create initiatives, approve transformations, or promote inferred/proposed evidence. Later slices may use this output to create an explicitly reviewed remediation initiative and scenario through existing governed write paths.

## Product boundary

The projection owns only EA facts and EA decisions. It does not ingest or duplicate Semantic Data Portal assets, pg-erd-cloud schemas, LineageWeave inferred lineage, Keyverse identities, naruon workspace state, or contextual-orchestrator proposals. Cross-product enrichment must arrive through published contracts/events with tenant identity, truth origin, provenance, and replay/idempotency semantics. Service-to-service direct application-table SQL remains prohibited.

## Consequences

- A buyer can ask which applications and capabilities are exposed to a technology lifecycle change and receive explicit evidence provenance plus a concrete next action.
- Late-recorded backfills do not rewrite an earlier audit view; the same valid-time question can return different evidence only when the requested recorded-time cutoff changes.
- Missing capability or support evidence is visible as a decision-blocking state rather than being mistaken for no impact.
- The first slice stays deterministic and does not require an LLM for catalog/architecture logic.
- Cross-domain impact expansion remains additive: physical schema, data product, dashboard/model/agent, and transformation evidence can be projected later without moving another product's source of truth into this database.

## Verification

`database/tests/zz_verify_technology_change_impact.sql` exercises the real PostgreSQL boundary. It proves late-recorded capability evidence is excluded at an earlier system cutoff, the same evidence becomes visible after its recording time, truth/evidence identities survive traversal, support-horizon and end-of-life classifications produce deterministic actions, an invalid horizon fails closed, and an unknown technology version cannot cross the active tenant boundary. CI applies migration 0015 on a clean database, rehearses upgrade from migration 0014, verifies the function exists at the upgraded boundary, checks the exact migration ledger count, and then executes all SQL invariants under the repository's runtime test role.
