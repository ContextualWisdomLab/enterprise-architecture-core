# ADR 0023: Expose a purpose-bound portfolio assessment read slice

- **Status:** Accepted for the current implementation line.
- **Date:** 2026-08-20

## Context

The normalized assessment model already stores versioned frameworks, scales,
dimensions, cycles, scores, valid-time intervals, recorded-time evidence, and
truth/provenance fields. The buyer gap is not another write model; it is the
absence of a safe read that can answer which assessment facts are visible for
one architecture object at two explicit cutoffs.

## Decision

Expose `GET /v1/architecture-objects/{architecture_object_id}/portfolio-assessments`
with required `valid_at` and `recorded_at` timestamps and optional bounded
framework/cycle selectors. The runtime verifies a dedicated
`EA_PORTFOLIO_ASSESSMENT_READ_ROLES` Keyverse role and calls only
`architecture_core.read_portfolio_assessment_for_tenant(...)`.

The PostgreSQL function binds the verified tenant transaction-locally, applies
valid/system cutoffs to the object revision and normalized assessment facts,
filters superseded/rejected facts, and preserves inferred/proposed truth labels
for human review. The response is a collection of facts, not a computed score
or an authorization decision.

## Consequences

- Buyers can retrieve reproducible, tenant-scoped assessment evidence for one
  object without direct table SQL.
- The first slice is intentionally headless; aggregate scoring, portfolio-wide
  comparison, mutation, and UI remain separate product work.
- The next product step is to define the scoring/read model only after buyer
  feedback confirms which cross-object comparison and action are needed.
