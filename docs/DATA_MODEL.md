# Data Model

## Core identity

- `tenant_record`: tenant boundary and canonical tenant code.
- `object_type`: controlled object taxonomy.
- `architecture_object`: common UUIDv7 object identity and canonical URI.
- `object_revision`: versioned title, description, evidence, truth origin, and
  bitemporal validity.

Canonical asset URIs are checked against the referenced tenant code, object
type code, and architecture object UUID. A syntactically valid but inconsistent
URI is rejected by the database.

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

## Assessment

Framework, dimension, scale, cycle, and object assessment are normalized so a
score never silently changes meaning when a framework version changes. These
tables are planned, not implemented in the foundation PR.

## Transformation

- `architecture_scenario` identifies a baseline cutoff.
- `scenario_change` stores an ordered delta.
- current-state records are unchanged until an approved change is executed.

These tables and the scenario projector are planned, not implemented in the
foundation PR.

## Integration

- `outbox_event` provides atomic publication and object-shaped JSON payloads.
- `projection_receipt` makes inbound event replay idempotent and validates the
  authority URI plus UUIDv7 event identity.
- `evidence_record` stores opaque evidence references and byte digests.
- `identity_link` stores Keyverse subject links, not credentials.
