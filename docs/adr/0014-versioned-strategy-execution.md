# ADR 0014: Versioned strategy execution facts

- **Status:** Accepted
- **Date:** 2026-08-17

## Context

Enterprise Architecture needs to connect portfolio evidence to decisions that a buyer can act on: an objective, a bounded remediation initiative, the objective that initiative advances, and ordered target milestones. Treating these as mutable planning fields would erase the evidence and timing that justified an architecture decision. Treating them as project-management records would also violate the EA Core boundary by duplicating execution systems.

ISO/IEC/IEEE 42010:2022 treats architecture descriptions as records of architecture concerns, decisions, and relationships. PostgreSQL 18 range and exclusion semantics provide an executable way to reject overlapping current authoritative facts, while row-level security provides defense-in-depth tenant isolation at the relational boundary.

## Decision

EA Core stores four normalized tenant-owned relations: `strategy_objective`, `remediation_initiative`, `initiative_objective_link`, and `initiative_milestone`.

Each fact uses UUIDv7 identity, explicit valid time (`valid_from`/`valid_to`), system-recorded time (`recorded_at`/`superseded_at`), truth origin, and tenant-bound evidence when the truth is `authoritative` or `observed`. Current authoritative facts for the same semantic identity cannot overlap. Initiative-objective links must be valid inside both referenced fact intervals. Milestone validity and `target_at` must be inside the initiative interval, and milestone sequence numbers are positive.

Decision meaning is append-preserving: semantic columns cannot be edited in place. A correction supersedes the recorded fact once and appends a replacement. Inferred or proposed facts remain reviewable and cannot silently become authoritative.

Milestones are architecture-decision targets only. EA Core does not own task assignment, work-item state, sprint/project execution, staffing, or delivery telemetry. Those remain external execution-system responsibilities. Scenario baselines, ordered scenario deltas, approved transformations, and transformation history remain a separate subsequent milestone under ADR 0008.

## Consequence

Buyers can trace a remediation initiative back to an evidence-bearing objective and a time-bounded architecture target without rewriting history. Real PostgreSQL acceptance must prove evidence requirements, interval containment, immutable meaning, one-time supersession, milestone ordering/target bounds, and cross-tenant denial. The additional normalized relations increase migration and projection work, but they preserve product boundaries and create a reliable substrate for the Technology Change Impact & Target-State Planner rather than a second project-management system.

## Evidence

- ISO/IEC/IEEE 42010:2022, architecture-description terminology and decision context.
- PostgreSQL 18 documentation for range types, exclusion constraints, constraints, and row-security policies.
- `database/migrations/0011_strategy_execution.sql`.
- `database/tests/zz_verify_strategy_execution.sql`.
