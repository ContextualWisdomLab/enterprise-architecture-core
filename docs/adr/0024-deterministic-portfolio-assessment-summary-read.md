# ADR 0024: Deterministic portfolio assessment summary read

- **Status:** Accepted for the current implementation line.
- **Date:** 2026-08-20

## Context

ADR 0023 exposes normalized portfolio assessment facts for one architecture
object at explicit valid-time and recorded-time cutoffs. Buyers also need a
compact evidence state and next action, but scores from different framework
scales cannot be averaged without an approved normalization policy.

## Decision

Expose `GET
/v1/architecture-objects/{architecture_object_id}/portfolio-assessment-summary`
with the same cutoffs, selectors, tenant boundary, and dedicated
`EA_PORTFOLIO_ASSESSMENT_SUMMARY_READ_ROLES` Keyverse allow-list as the raw
assessment read. Reuse the validated `read_portfolio_assessment_for_tenant(...)`
read port and group only identical framework code/title/version, scale,
dimension, and cycle facts.

Each group reports its count, same-scale score bounds, labels, truth statuses,
evidence count, and deterministic state/action. Missing evidence returns
`evidence_gap` and `collect_assessment_evidence`; inferred or proposed facts
with evidence return `review_required` and `review_assessment_truth`; otherwise
the group returns `evidence_complete` and `use_assessment_evidence`. An empty
collection returns `no_assessments` and `collect_portfolio_assessments`.

## Consequences

- Buyers receive a compact read model without direct SQL or a presentation UI.
- The endpoint does not average or normalize scores across scales, and it does
  not mutate assessment history or promote inferred/proposed truth.
- Cross-scale scoring, portfolio-wide list workflow, and UI require a separate
  approved product and semantic decision.

## Verification

OpenAPI/runtime validation, parser and summary tests, repository validation,
and real PostgreSQL acceptance of the reused 0049 read port verify the
tenant, cutoff, truth, evidence, and no-cross-scale boundaries.
