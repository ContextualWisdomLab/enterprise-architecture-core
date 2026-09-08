# Context Assertion admission migration provenance traceability

## Problem

The candidate Context Assertion projection receipt was introduced incrementally in migrations 0051-0055. The earlier 0053-0055 form added exact-looking schema, event-profile, message-profile, and admission-version columns with constant `DEFAULT` values. PostgreSQL applies a constant `ADD COLUMN ... DEFAULT` to existing rows logically even when it can avoid rewriting those rows physically. That is acceptable for ordinary data migration, but not for admission evidence: a provisional row does not prove that the released CGC SDK actually returned the later exact profile or admission identity.

EA therefore must not promote a compatibility label, a dataschema URI, or a structured CloudEvent media type into stronger admission provenance during DDL upgrade. The consumer projection may retain only identity that came from the admitted Context Assertion receipt.

## Domain decision

`architecture_core.context_assertion_projection_receipt` remains an EA-side immutable receipt extension of the generic `projection_receipt`; it does not acquire upstream product authority. Exact CGC schema/profile/message-profile/admission identity is evidence, not derivable metadata.

For the unreleased candidate migration sequence:

- 0053, 0054, and 0055 must fail closed if any Context Assertion detail row already exists at that migration boundary;
- no exact admission-identity column may use a DDL default to backfill an existing row;
- a clean install proves the table empty before adding the new `NOT NULL` identity columns without defaults;
- every later insert must supply the exact values copied from `ContextAssertionAdmission`;
- an environment that persisted provisional rows must re-admit them from immutable upstream event/provenance evidence, or rebuild the provisional projection store, instead of rewriting immutable history to make it look admitted under a contract that was not actually observed.

This keeps the six-value truth/origin model and Context Fabric authority boundary intact: migration mechanics cannot upgrade evidence authority.

## RED and minimum causal repair

Test-only commit `a05aaf61b30294cb80157469a1531b49ea58526c` added `tests/test_context_assertion_migration_provenance.py`. The regression requires an explicit empty-table fail-closed guard in each evidence-identity migration and rejects `ADD COLUMN ... DEFAULT` for the new schema/profile/admission identity columns. A focused exact-source probe against the then-current 0053-0055 blobs observed all nine intended failures: three missing empty-table guards and six synthetic-default paths.

The minimum production repair is contained in `df184e5f27635629bae482009d902010ea5acce4`, `5061b8f7d7bc334718dee91c371cfe55614a7f4b`, and `4a4ec322a2d818e40470f2a9b11d2457e91199f2`. It changes only candidate migration semantics: existing provisional rows now stop the migration, and clean empty tables receive exact identity columns with no default. Test hygiene commit `27878f1640215f69d8dea7f06baa2dee2eebfa5c` preserves the same regression under repository Ruff import policy.

A focused exact-source replay of the checked-in regression against the repaired migration blobs is GREEN. Hosted exact-head Python/PostgreSQL/coverage/security evidence has not materialized for this stacked Draft and is not transferred from predecessors; the PR remains Draft and non-mergeable until the live stack/control plane is repaired and the unchanged exact head reacquires the full repository gates.

## Recovery and release rule

These migrations are candidate-only and must not be interpreted as permission to mutate a released receipt history in place. If a non-authoritative environment previously applied the provisional migrations and wrote Context Assertion detail rows, stop the upgrade, retain the original event/provenance sources, and re-admit or rebuild the projection after the final released CGC contract is available. Do not assign exact profile/admission values by inference.

No EA quarantine projection may become release authority until the corresponding CGC Context Assertion contract is protected, versioned, published, and independently proven by its conformance/admission/package/SBOM/provenance gates.

## Reference

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.7. Modifying tables*. https://www.postgresql.org/docs/18/ddl-alter.html
