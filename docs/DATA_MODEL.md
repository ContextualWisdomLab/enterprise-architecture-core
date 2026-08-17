# Data Model

## Core identity

- `tenant_record`: tenant boundary and canonical tenant code.
- `object_type`: controlled object taxonomy.
- `architecture_object`: common UUIDv7 object identity and canonical URI.
- `object_revision`: versioned title, description, evidence, truth origin, and
  bitemporal validity.

Canonical asset URIs are checked against the referenced tenant code, object
type code, and architecture object UUID. A syntactically valid but inconsistent
URI is rejected by the database. Tenant codes, object-type codes, and the
identity-bearing tenant/object/type/URI fields of an architecture object are
immutable after creation because they participate in stable external
identifiers. Renames belong in temporal display metadata rather than in
canonical identity.

`architecture_object` intentionally carries no duplicate lifecycle-status
column. Lifecycle at a requested valid/system time is derived from the
normalized `lifecycle_interval` history.

## Typed extensions

- `business_capability`
- `organization_unit`
- `application_record`
- `application_interface`
- `technology_provider`
- `technology_component`
- `technology_version`

The foundation includes the seven inventory extensions listed above.
`architecture_objective` and `transformation_initiative` are planned for the
scenario milestone and are not represented as completed schema in this PR.

Tenant-owned extension tables use `(tenant_record_id, architecture_object_id)`
as their composite primary and foreign key. Database type-guard triggers also
require the referenced `architecture_object.object_type_id` to resolve to the
extension's exact object type code, so an application cannot be persisted as a
business capability or another contradictory typed record. This preserves the
3NF common-identity pattern without weakening domain type integrity. Provider
and version associations are represented by `architecture_relation`, rather
than duplicated foreign keys in extension tables.

`application_record` intentionally carries no business-criticality column.
Business criticality is represented through the versioned assessment model so a
score cannot disagree with the framework, dimension, scale, cycle, or evidence
that defines its meaning.

## Relationships and lifecycle

- `relation_type` controls permitted source and target object categories.
- `architecture_relation` stores temporal, evidence-backed source/target facts.
- `lifecycle_phase` defines an ordered vocabulary.
- `lifecycle_interval` records time-bounded object phases.

Database triggers reject relation endpoints whose object types contradict the
relation type. GiST exclusion constraints prevent overlapping current
**authoritative** object revisions and identical authoritative architecture
relations. `observed`, `inferred`, and `proposed` assertions may overlap an
authoritative fact so reviewers can compare evidence without silently promoting
the proposal. Identity links and lifecycle intervals remain non-overlapping
while active, because those tables do not expose the truth-status vocabulary.
Superseded system-time history remains queryable rather than being hard-deleted.

`authoritative` and `observed` object revisions and architecture relations must
reference an `evidence_record`; `inferred`, `proposed`, `superseded`, and
`rejected` remain evidence-optional because the shared Context Assertion
contract does not require provenance for those truth origins. The composite
foreign keys keep an evidence row inside the same relational tenant, and the
`evidence_record_tenant_guard` additionally requires the tenant segment inside
`evidence_uri` to equal the row's `tenant_record.tenant_code`. Evidence from a
different CWL authority remains valid when it names the same tenant. This keeps
cross-product provenance usable without allowing a syntactically valid
foreign-tenant URI to masquerade as local evidence.

## Assessment

Portfolio assessment is normalized into six tenant-owned relations:

- `assessment_framework` identifies a framework code and immutable version
  label across a real-world validity interval.
- `assessment_scale` belongs to one framework version.
- `assessment_scale_value` defines the numeric value, label, and ordinal rank
  of one value in a scale.
- `assessment_dimension` belongs to one scale; its framework is derived through
  that scale rather than duplicated on the dimension row.
- `assessment_cycle` identifies a bounded review period for one framework
  version.
- `object_assessment` binds an architecture object to a dimension, cycle, scale
  value, truth origin, evidence reference, real-world validity, and
  system-recorded history.

The database verifies that an assessment value belongs to the dimension's scale
and that the cycle belongs to the same framework version derived through that
scale. `authoritative` and `observed` assessments require evidence; inferred and
proposed alternatives may coexist for review without silently becoming current
truth. A GiST exclusion constraint prevents overlapping current authoritative
assessments for the same object, dimension, and cycle. Composite tenant foreign
keys plus forced RLS preserve tenant isolation across the entire assessment
chain.

Assessment meaning is append-preserving. Scale, scale-value, and dimension rows
cannot be updated after insertion. Framework, cycle, and object-assessment
meaning likewise cannot be edited in place; those records may only acquire a
`superseded_at` value once, after which that timestamp is immutable. A correction
therefore supersedes the recorded fact and appends a replacement. This keeps the
original framework definition, score semantics, evidence link, and assessor
record queryable at the historical system-time cutoff instead of silently
rewriting prior portfolio decisions.

Framework version and scale semantics are therefore stable determinants of a
score. The write model does not copy framework identity onto dimensions or
objects merely for query convenience; projections may denormalize those facts
outside the authoritative relational store.

## Transformation

- `architecture_scenario` identifies a baseline cutoff.
- `scenario_change` stores an ordered delta.
- current-state records are unchanged until an approved change is executed.

These tables and the scenario projector remain planned and are not implemented
by the portfolio-assessment milestone.

## Integration

- `outbox_event` provides atomic publication and object-shaped JSON payloads.
- `projection_receipt` makes inbound event replay idempotent and validates the
  authority URI plus UUIDv7 event identity.
- `evidence_record` stores opaque, tenant-consistent evidence references and
  byte digests.
- `identity_link` stores Keyverse subject links, not credentials.

Operational event timestamps preserve system-time causality at the database
boundary: an outbox event cannot be marked published before its `recorded_at`,
and an inbound projection cannot be marked processed before its `received_at`.
The status/timestamp consistency checks remain orthogonal, so pending/processing
rows still have no terminal timestamp while published/processed rows require
one. These invariants are exercised on clean installation and on the migration
upgrade path.
