# ADR 0026: Retain Context Assertion projection receipt identity explicitly

- Status: Accepted for candidate integration; production activation remains release-gated.
- Bounded context: Cross-Domain Evidence / Enterprise Architecture Decision Plane ACL.

## Context

The Context Assertion connector promises that a consumer projection retains the producer authority, complete CloudEvent identity, schema/profile/admission versions, and provenance that were admitted by the released Context Graph Contracts SDK. The existing candidate receipt persisted `dataschema`, semantic profile identity/version, and admission version, but did not persist the admitted schema version as its own receipt dimension.

Inferring a schema version later by parsing `dataschema` text would move Shared Kernel interpretation into the EA consumer and could make historical receipt meaning depend on future URI parsing rules. It would also make the machine connector declaration stronger than the persisted evidence.

The Context Assertion detail receipt is keyed to the reusable `projection_receipt` parent. That parent already enforces canonical CWL source authority identity, UUIDv7 event identity, tenant isolation, immutable evidence identity, and a provider-neutral `schema_version` label. Provider neutrality is correct for the generic parent, but it also means the database must prevent a Context Assertion detail from being attached to a parent whose immutable schema identity names another projection contract.

## Decision

`architecture_core.context_assertion_projection_receipt` retains `context_schema_version` as an explicit immutable receipt value alongside `context_profile_id`, `context_profile_version`, and `admission_version`.

Migration 0054 backfills existing candidate v1 rows with schema version `1` because migration 0051 already constrains every such row to the exact Context Assertion v1 `dataschema`. The migration then removes the default. Every future receipt must therefore copy the schema version supplied by the admitted CGC SDK receipt instead of manufacturing a local default or parsing it from a URI. A database check binds this candidate lane to schema version 1.

Migration 0051 also validates the parent receipt relationship before creating the Context Assertion detail. The generic parent must carry the exact `context-assertion/v1` schema identity. A generic receipt for another schema remains valid for its own bounded context, but cannot be reinterpreted as admitted Context Assertion evidence. Because migration 0019 makes the parent evidence identity immutable, this relationship cannot be changed after the detail is admitted.

The receipt continues to preserve the complete CloudEvent identity, source authority and provenance. It does not promote foreign truth to EA authority, copy producer source or tables, or make EA the owner of the Context Assertion contract.

## Consequences

EA can prove that the physical projection receipt satisfies the same `source authority -> CloudEvent identity -> schema version -> profile id -> profile version -> admission version -> provenance` sequence declared by the connector ACL. Canonical source and event identity remain enforced by the generic parent, while the Context Assertion ACL additionally binds that parent to the correct schema family. Historical candidate rows remain semantically unchanged, while future inserts fail closed if either the parent schema identity or the admitted detail identity disagrees.

The PostgreSQL contract test `database/tests/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz_verify_context_assertion_parent_identity.sql` supplies a valid generic receipt for an unrelated schema and requires the Context Assertion detail insert to fail with a check violation. This closes the persistent receipt-confusion case without narrowing the provider-neutral generic receipt model.

This is still candidate integration evidence. EA must not enable or describe the Context Assertion projection as production-compatible until an immutable protected CGC release exports the matching schema/profile/admission identity and passes the existing release, conformance, package, SBOM, provenance and source-binding gates.
