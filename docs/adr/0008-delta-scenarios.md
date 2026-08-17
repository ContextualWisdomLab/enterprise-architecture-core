# ADR 0008: Represent target architecture as scenario deltas

- **Status:** Accepted and implemented by migration 0012
- **Date:** 2026-08-16

## Context

Target-state planning must compare alternatives without copying or mutating the authoritative architecture graph. A copied graph loses a stable connection to the exact real-world and system-recording cutoffs from which the alternative was derived, while in-place edits destroy auditability.

## Decision

A scenario records one immutable baseline anchor and an append-only ordered sequence of bounded object-presence deltas rather than copying the entire architecture graph.

The baseline stores both `baseline_valid_at` and `baseline_recorded_at`. The projector reconstructs baseline membership from authoritative `object_revision` facts that were valid at the real-world cutoff and already recorded at the system-time cutoff. Late-arriving or subsequently superseded records therefore cannot silently rewrite an existing baseline.

Each `scenario_object_delta` has a positive sequence number, a tenant-bound architecture object, a target-effective interval, explicit truth status, and evidence when authoritative or observed. Sequence numbers are never reused. Corrections append a later delta; semantic fields are immutable. At the scenario target time, the latest active non-rejected, non-superseded delta for an object wins over baseline presence. The projector exposes presence, origin, applied sequence, and truth status rather than promoting proposed or inferred state to authoritative truth.

`architecture_scenario`, `scenario_baseline`, and `scenario_object_delta` use composite tenant foreign keys and forced PostgreSQL RLS. Scenario history cannot be hard-deleted. The baseline is entirely immutable; scenario and delta meaning can only receive a one-time `superseded_at` marker before replacement/continuation is appended.

This slice deliberately projects object presence only. Relation deltas, transformation execution/history, cross-domain evidence projections, and buyer UI remain separate later slices. The design is not an arbitrary meta-model editor or workflow engine.

## Consequences

Current authoritative truth remains untouched while alternative target states can be compared deterministically and audited against exact bitemporal cutoffs. A scenario without an accessible immutable baseline fails closed, cross-tenant targets are rejected, and deltas beginning after the scenario target time cannot be appended.

## Executable evidence

- `database/migrations/0012_scenario_projection.sql`
- `database/tests/zz_verify_scenario_projection.sql`
- `.github/workflows/ci.yml` previous-boundary migration rehearsal
