# Data Model

## Core identity

- `tenant_record`: tenant boundary.
- `object_type`: controlled object taxonomy.
- `architecture_object`: common object identity and canonical URI.
- `object_revision`: versioned title, description, evidence, truth origin, and
  bitemporal validity.

## Typed extensions

- `business_capability`
- `organization_unit`
- `application_record`
- `application_interface`
- `technology_provider`
- `technology_component`
- `technology_version`

The first migration includes the seven inventory extensions listed above.
`architecture_objective` and `transformation_initiative` are planned for the
scenario milestone and are not represented as completed schema in this PR.

Tenant-owned extension tables use `(tenant_record_id, architecture_object_id)`
as their composite primary and foreign key. This prevents an object identifier
from being attached across tenants while keeping type-specific attributes in
separate 3NF relations. Provider and version associations are represented by
`architecture_relation`, rather than duplicated foreign keys in extension
tables.

## Relationships and lifecycle

- `relation_type` controls permitted semantic relations.
- `architecture_relation` stores temporal, evidence-backed source/target facts.
- `lifecycle_phase` defines an ordered vocabulary.
- `lifecycle_interval` records time-bounded object phases.

## Assessment

Framework, dimension, scale, cycle, and object assessment are normalized so a
score never silently changes meaning when a framework version changes.

## Transformation

- `architecture_scenario` identifies a baseline cutoff.
- `scenario_change` stores an ordered delta.
- current-state records are unchanged until an approved change is executed.

## Integration

- `outbox_event` provides atomic publication.
- `projection_receipt` makes inbound event replay idempotent.
- `evidence_record` stores opaque evidence references and byte digests.
- `identity_link` stores Keyverse subject links, not credentials.
