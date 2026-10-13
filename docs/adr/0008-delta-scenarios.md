# ADR 0008: Represent target architecture as scenario deltas

- **Status:** Accepted and implemented by migrations 0012-0013
- **Date:** 2026-08-16

## Context

Target-state planning must compare alternatives without copying or mutating the authoritative architecture graph. A copied graph loses a stable connection to the exact real-world and system-recording cutoffs from which the alternative was derived, while in-place edits destroy auditability.

A relation-only target-state edit also cannot be treated independently from object presence. A requested-present edge whose source or target is absent in the same target state would create a dangling graph that cannot represent a deployable architecture decision.

## Decision

A scenario records one immutable baseline anchor and append-only ordered object and relation presence deltas rather than copying the entire architecture graph.

The baseline stores both `baseline_valid_at` and `baseline_recorded_at`. The projectors reconstruct baseline membership from authoritative facts that were valid at the real-world cutoff and already recorded at the system-time cutoff. Late-arriving or subsequently superseded records therefore cannot silently rewrite an existing baseline.

Each `scenario_object_delta` has a positive sequence number, a tenant-bound architecture object, a target-effective interval, explicit truth status, and evidence when authoritative or observed. Sequence numbers are never reused inside the object-delta stream. Corrections append a later delta; semantic fields are immutable. At the scenario target time, the latest active non-rejected, non-superseded delta for an object wins over baseline presence. `project_scenario_objects(uuid)` exposes presence, origin, applied sequence, and truth status rather than promoting proposed or inferred state to authoritative truth.

Each `scenario_relation_delta` identifies a typed edge by `relation_type_id`, source object, and target object. It has the same target-effective, append-preserving truth/evidence semantics and a positive non-reusable sequence inside the relation-delta stream. The existing authoritative relation-type guard is reused so a target-state edge cannot evade the source/target taxonomy that applies to `architecture_relation`.

`project_scenario_relations(uuid)` reconstructs authoritative relation facts at the same immutable bitemporal baseline, applies the latest active relation delta per typed endpoint tuple, and then composes with `project_scenario_objects(uuid)`. A requested-present relation is not emitted as active when either projected endpoint is absent. Instead the row remains auditable with `is_present=false` and explicit `endpoint_integrity_code` (`source_absent`, `target_absent`, or `both_absent`). The projector never invents or promotes an endpoint to satisfy an edge.

`architecture_scenario`, `scenario_baseline`, `scenario_object_delta`, and `scenario_relation_delta` use composite tenant foreign keys and forced PostgreSQL RLS. Scenario history cannot be hard-deleted. The baseline is entirely immutable; scenario and delta meaning can only receive a one-time `superseded_at` marker before replacement/continuation is appended.

This decision projects object and relation presence only. Transformation execution/history, cross-domain evidence projections, impact traversal, and buyer UI remain separate later slices. The design is not an arbitrary meta-model editor or workflow engine.

## Consequences

Current authoritative truth remains untouched while alternative target-state graphs can be compared deterministically and audited against exact bitemporal cutoffs. A scenario without an accessible immutable baseline fails closed, cross-tenant targets are rejected, and deltas beginning after the scenario target time cannot be appended.

Endpoint-aware relation projection prevents a scenario from presenting a dangling relation as active when its source or target object has been removed. The relation row is retained with explicit requested intent and endpoint-integrity evidence so an architect can distinguish an intentional relation removal from a relation suppressed by target-state object changes.

Object and relation delta streams currently have independent positive sequence spaces. The final projectors are deterministic because each stream resolves latest intent per semantic target and relation activity is composed against the final object projection; a future transformation-execution ledger may introduce one cross-stream execution order if product requirements need event-by-event replay rather than target-state comparison.

## Executable evidence

- `database/migrations/0012_scenario_projection.sql`
- `database/migrations/0013_scenario_relation_projection.sql`
- `database/tests/zz_verify_scenario_projection.sql`
- `database/tests/zz_verify_scenario_relation_projection.sql`
- `.github/workflows/ci.yml` clean-install and previous-boundary migration rehearsal
