# ADR 0026: Retain Context Assertion projection receipt identity explicitly

- Status: Accepted for candidate integration; production activation remains release-gated.
- Bounded context: Cross-Domain Evidence / Enterprise Architecture Decision Plane ACL.

## Context

The Context Assertion connector promises that a consumer projection retains the producer authority, complete CloudEvent identity, schema/profile/admission versions, and provenance that were admitted by the released Context Graph Contracts SDK. The existing candidate receipt persisted `dataschema`, semantic profile identity/version, and admission version, but did not persist the admitted schema version as its own receipt dimension.

Inferring a schema version later by parsing `dataschema` text would move Shared Kernel interpretation into the EA consumer and could make historical receipt meaning depend on future URI parsing rules. It would also make the machine connector declaration stronger than the persisted evidence.

## Decision

`architecture_core.context_assertion_projection_receipt` retains `context_schema_version` as an explicit immutable receipt value alongside `context_profile_id`, `context_profile_version`, and `admission_version`.

Migration 0054 backfills existing candidate v1 rows with schema version `1` because migration 0051 already constrains every such row to the exact Context Assertion v1 `dataschema`. The migration then removes the default. Every future receipt must therefore copy the schema version supplied by the admitted CGC SDK receipt instead of manufacturing a local default or parsing it from a URI. A database check binds this candidate lane to schema version 1.

The receipt continues to preserve the complete CloudEvent identity, source authority and provenance. It does not promote foreign truth to EA authority, copy producer source or tables, or make EA the owner of the Context Assertion contract.

## Consequences

EA can prove that the physical projection receipt satisfies the same `schema_version -> profile_id -> profile_version -> admission_version` identity sequence declared by the connector ACL. Historical candidate rows remain semantically unchanged, while future inserts fail closed if the consumer does not supply the admitted schema version.

This is still candidate integration evidence. EA must not enable or describe the Context Assertion projection as production-compatible until an immutable protected CGC release exports the matching schema/profile/admission identity and passes the existing release, conformance, package, SBOM, provenance and source-binding gates.
