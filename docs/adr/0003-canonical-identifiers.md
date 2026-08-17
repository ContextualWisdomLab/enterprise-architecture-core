# ADR 0003: Use authority-scoped canonical references

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Cross-product references use UUIDv7-backed CWL URNs defined by
`context-graph-contracts`. Provider IDs and emails are external keys, not
canonical identities.

EA Core issues references in the form
`urn:cwl:{tenant_code}:ea_core:{object_type_code}:{uuidv7}`. The tenant code,
object-type code, and an architecture object's assigned type are
identity-bearing determinants and are immutable after creation. The canonical
URN is derived through the normalized reference projection rather than stored
as a duplicate writable column.

## Consequence

Ownership is visible in each reference and migration between providers does not
change enterprise identity. Reclassification that would change a canonical
object type is modeled as a new architecture object plus an explicit governed
relationship or transformation, not as an in-place identity rewrite.

The database acceptance suite verifies both exact projection and determinant
immutability. Compatibility with other CWL products remains gated on an
immutable compatible `context-graph-contracts` release and its conformance
fixtures; EA Core does not redefine authority or truth semantics independently.
