# ADR 0013: Normalize versioned portfolio assessment semantics

- **Status:** Accepted
- **Date:** 2026-08-17

## Context

Enterprise architects need portfolio scores such as technology risk and business
fit to remain interpretable after frameworks, scales, and review cycles change.
A bare score on an application or technology record would duplicate assessment
meaning, make historical comparison ambiguous, and allow inferred output to be
mistaken for approved architecture truth. In-place edits to a framework, scale,
value, dimension, cycle, or recorded assessment would create the same ambiguity
by changing what a historical decision appears to have meant.

## Decision

Store portfolio assessment as normalized tenant-owned facts:

1. `assessment_framework` identifies a named framework and immutable version
   label over real-world validity.
2. `assessment_scale` belongs to one framework version and
   `assessment_scale_value` owns its allowed numeric value, label, and ordinal
   rank.
3. `assessment_dimension` belongs to one scale. The dimension's framework is
   derived through that scale rather than duplicated on the dimension row.
4. `assessment_cycle` defines a bounded review interval for one framework
   version.
5. `object_assessment` binds an architecture object to one dimension, cycle,
   allowed scale value, truth origin, provenance evidence, valid time, and
   system-recorded history.

The database rejects a scale value that is not from the dimension's scale and a
cycle whose framework differs from the framework derived through the dimension
scale. Current authoritative assessments for the same object, dimension, and
cycle cannot overlap. `authoritative` and `observed` assessments require an
evidence reference. `inferred` and `proposed` assessments may coexist for human
review but never silently replace authoritative facts.

Assessment definitions and recorded assessment content are append-preserving.
Scale, scale-value, and dimension rows are immutable after insertion. Framework,
cycle, and object-assessment meaning is likewise immutable; their only allowed
history transition is recording `superseded_at` once. Corrections therefore
supersede the affected fact and append a replacement rather than rewriting an
existing decision. The supersession timestamp itself cannot subsequently be
moved or cleared.

All six relations use composite tenant foreign keys and forced PostgreSQL row
level security. Query/search projections may denormalize these semantics, but
the authoritative write model does not.

## Consequences

- A score is reproducibly interpretable in its exact framework/version/scale
  and review cycle.
- Framework and scoring-definition changes create new versioned facts instead
  of rewriting historical meaning.
- A correction leaves the previous recorded fact queryable for audit and
  transformation-history reconstruction.
- Buyer-facing portfolio matrices can compare applications and technologies
  without embedding mutable scoring metadata on inventory objects.
- Future objective, initiative, scenario, and transformation milestones can
  consume stable assessments without becoming assessment authorities.
- The additional joins and append-preserving correction flow are intentional in
  the authoritative 3NF write model; read projections may optimize decision
  views separately.

## Verification

`database/tests/zz_verify_portfolio_assessment.sql` exercises a real PostgreSQL
clean install for semantic cross-reference rejection, authoritative evidence,
authoritative overlap exclusion, inferred coexistence, tenant RLS, rejection of
retrospective assessment-meaning edits, one-time supersession, and rejection of
supersession-timestamp rewriting. `.github/workflows/ci.yml` separately rehearses
upgrade from migrations 0001-0009 to migration 0010 and verifies the migration
ledger and resulting table set.
