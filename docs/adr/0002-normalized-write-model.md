# ADR 0002: Use a normalized relational write model

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

PostgreSQL third-normal-form tables are authoritative. Graph, search, portfolio,
and interoperability views are derived projections. A value that is fully
functionally dependent on normalized identity determinants is not persisted as
a second writable fact.

For canonical EA object references, the write model therefore stores only the
tenant, object type, and UUIDv7 object identity. The
`architecture_core.architecture_object_reference` view derives the CWL asset
URN by joining `tenant_record.tenant_code`, `object_type.object_type_code`, and
`architecture_object.architecture_object_id` with the fixed `ea_core`
authority segment.

## Consequence

Business constraints, temporal history, and transactional updates remain
explicit while graph and interoperability projections can be rebuilt. There is
no stored `canonical_asset_uri` column to drift from its determinants. Identity
segments used by the projection are immutable after creation, so an externally
issued canonical reference remains stable rather than requiring a cascading
rewrite.

Executable PostgreSQL acceptance reconstructs an exact canonical URI through
the view and rejects mutation of identity-bearing tenant, object-type, and
object assignment fields.
