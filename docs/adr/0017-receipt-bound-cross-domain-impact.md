# ADR 0017: Receipt-bound cross-domain impact projection

- **Status:** Accepted
- **Date:** 2026-08-17
- **Shipping state:** Accepted on this feature branch; not protected-main shipped truth until the owning PR integrates.
- **Depends on:** ADR 0004 (bitemporal history), ADR 0007 (evidence/truth status), ADR 0012 (ecosystem connectors), ADR 0016 (bitemporal technology impact projection).

## Context

The EA-owned technology impact path now identifies applications and capabilities exposed to a technology lifecycle change. A buyer still needs to understand whether those applications are connected to physical database/schema evidence and Data/AI products such as data products, dashboards, models, and AI agents. Those objects are not Enterprise Architecture Core authority: pg-erd-cloud owns physical schema evidence, Semantic Data Portal owns Data/AI catalog and trust context, and LineageWeave owns inferred/proposed semantic-lineage evidence.

Copying their mutable records into the EA write model, querying their application tables, or accepting an inferred lineage result as authoritative would break product boundaries and make historical impact decisions unverifiable. The EA Decision Plane instead needs a small, normalized projection boundary that records only canonical foreign identity, the processed event receipt that supplied the projection, bitemporal applicability, and the source truth status needed to decide whether the evidence is review-ready.

The existing `projection_receipt` table already provides tenant-scoped event identity, source URI, payload SHA-256, schema version, receipt time, process time, status, and replay identity. This decision reuses that primitive instead of defining a second event ledger, then strengthens it so a malformed source string or later terminal-record rewrite cannot invalidate historical projection evidence.

## Decision

Migrations `0016_cross_domain_impact_projection.sql`, `0017_cross_domain_projection_replay_guard.sql`, `0018_projection_source_uri_contract.sql`, and `0019_projection_receipt_history_guard.sql` add the bounded cross-domain projection boundary and harden its receipt evidence. Migration 0018 promotes the existing 0005 source grammar guard to the explicit cross-domain contract name rather than layering an identical check.

`external_context_reference` stores only immutable foreign canonical identity: tenant, UUIDv7 local reference identifier, owning product code, canonical object URI, object kind, and recording time. It does not store foreign titles, descriptions, schema definitions, glossary content, certification, lineage graphs, credentials, or other source-of-truth payloads. The canonical URI must encode the same tenant, authority, and kind as the row. The current accepted authority/kind boundary is deliberately narrow:

- `pg_erd_cloud` -> `database_schema`;
- `semantic_data_portal` -> `data_product`, `dashboard`, `model`, or `ai_agent`.

`application_context_projection` records a receipt-bound assertion between one EA `application_record` and one external reference. It carries the projection relation code, explicit truth status, independent valid-time interval, system recording time, and optional supersession time. Composite tenant foreign keys, forced RLS, immutable projection meaning, one-time supersession, no hard delete, and active-interval exclusion preserve tenant and history semantics.

The projection source is derived from the referenced `projection_receipt.event_source_uri`; it is not copied into a second column. The existing 0005 guard already enforces the exact Context Graph canonical-authority URI grammar, and migration 0018 promotes that guard to `projection_receipt_source_uri_format` without a second equivalent check. This closes the legacy possibility that a forged prefix or appended segment could preserve the tenant/product positions consumed by `split_part`. Only processed receipts whose process time is no later than the projection recording time may create projection facts. Source responsibility is enforced at insertion:

- pg-erd-cloud may project only its physical-schema canonical references and only as `observed` evidence;
- Semantic Data Portal may project only its own canonical Data/AI references;
- LineageWeave may project links to existing canonical references only as `inferred` or `proposed` truth and therefore can never silently create authoritative EA decision evidence.

The receipt/fact composite uniqueness in migration 0017 makes repeated delivery of the same external event idempotent even for inferred/proposed facts that are intentionally not covered by the authoritative/observed interval-exclusion rule.

Migration 0019 makes accepted receipt evidence append-preserving. Tenant/id/source/event-id/digest/schema/received-time identity fields are immutable after insertion; hard deletion is rejected; `processed` and `rejected` receipts are terminal and cannot later be rewritten. A failed receipt may still retry by re-entering `processing`, but once any processing attempt has begun the receipt can never return to the initial `received` state. This preserves retryability while preventing a receipt from being reset to the pre-attempt state; this row is not a separate per-attempt audit ledger and does not claim to preserve every transient retry status.

`project_application_context_impact(uuid,timestamptz,timestamptz)` returns the external impact evidence visible for one tenant-owned application at explicit valid-time and system-recording cutoffs. It returns the foreign canonical URI and authority, object kind, relation/truth status, source receipt/event identity, payload digest, evidence state, and deterministic buyer next-action code. Missing application or time cutoffs fail closed. Superseded/rejected facts and receipts not processed by the requested system cutoff are excluded.

Inferred/proposed projections always return `requires_truth_review` / `review_truth_origin`. Other complete projections return an object-specific next action such as `review_schema_dependency`, `review_data_product_impact`, `review_dashboard_impact`, `review_model_impact`, or `review_ai_agent_impact`. This projector is read-only and does not create initiatives, scenarios, transformations, or authoritative foreign facts.

## Product boundary

Enterprise Architecture Core owns the EA application anchor and the decision-time projection of received evidence. It does not become a data catalog, physical schema store, lineage engine, or cross-product graph authority. Foreign payloads remain in their owning products. Cross-product exchange remains event/contract based and service-to-service direct application-table SQL remains prohibited.

A LineageWeave event may identify a relationship involving canonical references owned by pg-erd-cloud or Semantic Data Portal, but the referenced object authority remains the canonical URI owner while the projection source remains LineageWeave. This separation is what allows inferred evidence to be useful without changing ownership or truth status.

## Consequences

- Technology Change Impact can continue from an affected application to receipt-backed schema and Data/AI evidence without importing another product's source of truth.
- Historical queries remain reproducible because valid time, system recording time, immutable processed receipt time, source event identity, and payload digest are all visible at the projection boundary.
- Cross-tenant references, malformed source URIs, authority/kind spoofing, unprocessed receipts, and ownership-incompatible source events fail closed.
- Replayed delivery of the same receipt-bound fact is idempotent.
- Processed/rejected receipt evidence cannot be hard-deleted or retroactively reclassified; failed receipt processing can still be retried through `processing` without resetting the receipt to an unattempted `received` state.
- LineageWeave evidence can enrich impact discovery but cannot become authoritative or decision-ready without an explicit reviewed authority path.
- Buyer-facing output tells the operator what to inspect or review next instead of treating missing provenance or inferred evidence as a completed remediation decision.
- The projection remains intentionally shallow. Later owner-produced events may add further canonical references or path semantics without turning EA Core into the foreign catalog or lineage graph.

## Verification

`database/tests/zz_verify_cross_domain_impact_projection.sql` proves the tables and projector exist, canonical foreign references are tenant/authority/kind bound, processed receipts are mandatory, pg-erd-cloud evidence remains observed, LineageWeave evidence cannot be promoted to authoritative, late-recorded evidence is excluded from earlier system-time queries, buyer next actions are deterministic, missing temporal cutoffs fail closed, and a tenant cannot project another tenant's application.

`database/tests/zz_verify_cross_domain_impact_replay.sql` replays the same LineageWeave receipt-bound inferred fact and requires a uniqueness failure rather than a duplicate projection row. `database/tests/zz_verify_projection_source_uri_guard.sql` proves a forged source string that preserves legacy split positions is rejected by the canonical-authority URI contract. `database/tests/zz_verify_projection_receipt_history.sql` proves a processed receipt cannot have its status, digest, or row history rewritten after it has supplied decision evidence and proves a failed receipt cannot regress to the initial `received` state before a retry.

Repository validation binds the resulting schema inventory to 38 tables, 411 validator-visible typed column declarations, 12 indexes, and 320 named constraints. The PostgreSQL CI lane must prove clean install, dynamic upgrade through migration 0020, migration-ledger integrity, all SQL invariants, and runtime RLS acceptance before this branch may be considered green.
