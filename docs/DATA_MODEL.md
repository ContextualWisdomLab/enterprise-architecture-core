# Data Model

## Core identity

- `tenant_record`: tenant boundary and canonical tenant code.
- `object_type`: controlled object taxonomy.
- `architecture_object`: common UUIDv7 object identity and canonical URI.
- `object_revision`: versioned title, description, evidence, truth origin, and bitemporal validity.

Canonical asset URIs are checked against the referenced tenant code, object type code, and architecture object UUID. A syntactically valid but inconsistent URI is rejected by the database. Tenant codes, object-type codes, and identity-bearing tenant/object/type/URI fields are immutable after creation because they participate in stable external identifiers. Renames belong in temporal display metadata rather than canonical identity.

`architecture_object` intentionally carries no duplicate lifecycle-status column. Lifecycle at a requested valid/system time is derived from normalized `lifecycle_interval` history.

## Typed inventory extensions

The foundation owns the seven typed inventory extensions below:

- `business_capability`
- `organization_unit`
- `application_record`
- `application_interface`
- `technology_provider`
- `technology_component`
- `technology_version`

Tenant-owned extension tables use `(tenant_record_id, architecture_object_id)` as their composite primary and foreign key. Database type-guard triggers require the referenced architecture object to have the extension's exact object type. Provider and version associations are represented by `architecture_relation`, rather than duplicated foreign keys in extension tables.

`application_record` carries no duplicated business-criticality column. Business criticality belongs to the versioned assessment model so a score cannot disagree with the framework, dimension, scale, cycle, or evidence that defines its meaning.

## Relationships and lifecycle

- `relation_type` controls permitted source and target object categories.
- `architecture_relation` stores temporal, evidence-backed source/target facts.
- `lifecycle_phase` defines an ordered vocabulary.
- `lifecycle_interval` records time-bounded object phases.

Database triggers reject relation endpoints whose object types contradict the relation type. GiST exclusion constraints prevent overlapping current authoritative object revisions and identical authoritative architecture relations. `observed`, `inferred`, and `proposed` assertions may coexist with authoritative facts for review. Identity links and lifecycle intervals remain non-overlapping while active. Superseded system-time history remains queryable rather than being hard-deleted.

`authoritative` and `observed` object revisions and architecture relations require an `evidence_record`. Composite foreign keys keep evidence inside the same relational tenant, while the evidence tenant guard requires the tenant segment in `evidence_uri` to match the row tenant. Cross-product evidence is valid only when it refers to the same tenant.

## Portfolio assessment

Portfolio assessment is normalized into six tenant-owned relations:

- `assessment_framework`: framework code and immutable version label.
- `assessment_scale`: scale owned by one framework version.
- `assessment_scale_value`: numeric value, label, and ordinal rank.
- `assessment_dimension`: assessment dimension owned by one scale.
- `assessment_cycle`: bounded review period for one framework version.
- `object_assessment`: architecture object, dimension, cycle, value, truth, evidence, valid time, and system history.

The database verifies that a value belongs to the dimension's scale and that a cycle belongs to the same framework version derived through that scale. Authoritative and observed scores require evidence. A GiST exclusion constraint prevents overlapping current authoritative assessments for the same object/dimension/cycle while inferred or proposed alternatives remain reviewable. Composite tenant foreign keys and forced RLS preserve tenant isolation.

Assessment meaning is append-preserving. Scale, scale-value, and dimension rows are immutable after insertion. Framework, cycle, and object-assessment meaning cannot be edited in place; those rows may acquire `superseded_at` once and must then be replaced with a new fact.

## Strategy execution decisions

Migration 0011 adds four normalized tenant-owned relations that turn assessment evidence into auditable architecture decisions without becoming a project-management store:

- `strategy_objective`: an evidence-bearing architecture objective with bitemporal history.
- `remediation_initiative`: a bounded architecture remediation decision.
- `initiative_objective_link`: a typed contribution from an initiative to an objective.
- `initiative_milestone`: an ordered architecture target with a target timestamp.

Authoritative and observed strategy facts require evidence. Current authoritative rows with the same semantic identity cannot overlap. Initiative-objective link validity must be contained in both the initiative and objective valid-time intervals. A milestone's valid interval and `target_at` must be contained in the initiative interval, and `sequence_number` must be positive.

Strategy meaning is immutable after insertion. Semantic correction uses one-time `superseded_at` plus a newly appended fact, preserving historical system-time queries. Forced RLS and composite tenant foreign keys protect all four relations. These milestones describe architecture decision targets only; project tasks, staffing, sprint state, and delivery telemetry remain external execution-system responsibilities.

## Scenarios and target-state projection

Migration 0012 implements the immutable object baseline of ADR 0008 with three normalized tenant-owned relations and one deterministic database projector:

- `architecture_scenario`: the versioned scenario decision, including one `target_valid_at` instant and explicit truth/evidence.
- `scenario_baseline`: the single immutable pair of `baseline_valid_at` and `baseline_recorded_at` cutoffs for a scenario.
- `scenario_object_delta`: append-only ordered object-presence changes with target-effective intervals, truth/evidence, and positive sequence numbers.
- `project_scenario_objects(uuid)`: a tenant-bound projection that overlays the latest active delta per object on the authoritative object-revision baseline.

Baseline membership is reconstructed from authoritative `object_revision` facts that were valid at `baseline_valid_at`, recorded no later than `baseline_recorded_at`, and not yet superseded at that system-time cutoff. This preserves the distinction between real-world validity and system-recording history: later backfills or later supersession do not silently rewrite an existing baseline.

Scenario object deltas never mutate authoritative architecture objects or revisions. A delta can only state whether an existing tenant-owned architecture object is present or absent in the scenario target state. The same object-delta sequence number cannot be reused. If an object has multiple active deltas, the highest sequence number wins at `target_valid_at`; corrections are appended rather than rewriting earlier decisions. The projection returns the resulting presence, whether it came from the baseline or a scenario delta, the applied sequence number, and the corresponding truth status.

Migration 0013 extends the same scenario without copying the authoritative graph:

- `scenario_relation_delta`: append-only ordered relation-presence intent identified by relation type plus tenant-bound source/target objects, with target-effective interval, truth origin, and evidence.
- `project_scenario_relations(uuid)`: reconstructs authoritative relations at the immutable baseline cutoffs, overlays the latest active relation delta per typed endpoint tuple, and joins the final object projection so a target-state relation cannot remain active when either endpoint is absent.

Relation deltas reuse the authoritative relation-type guard; a proposed target-state edge must therefore respect the same source/target object taxonomy as shipped architecture truth. Authoritative and observed relation deltas require evidence, semantic fields are immutable, sequence numbers are positive and non-reusable within the relation-delta stream, and history is corrected only by later deltas or one-time supersession. The relation projector exposes requested presence, baseline/delta origin, applied sequence, truth status, baseline and delta evidence identities, and `endpoint_integrity_code`. A requested-present relation with a missing target-state source or target is returned as not present with `source_absent`, `target_absent`, or `both_absent`; the projector never invents or promotes an endpoint merely to satisfy an edge.

An immutable baseline must exist before either delta type is appended. Baseline time cannot exceed the scenario target time, a delta cannot begin after that target, cross-tenant targets are rejected through composite foreign keys, and rejected/superseded deltas do not participate in the current projection. All scenario relations use forced RLS. Scenario history cannot be hard-deleted; baseline meaning is fully immutable, while scenario and delta records support only one-time supersession before replacement/continuation is appended.

This milestone projects object and relation presence for a deterministic target-state graph. Cross-domain event projection and buyer-facing scenario comparison UI remain later bounded slices; the scenario model is not an arbitrary meta-model editor, workflow engine, or substitute for another product's authoritative store.

## Transformation execution history

Migration 0014 binds an immutable target-state decision to governed execution history without turning the Enterprise Architecture Decision Plane into a project-management system:

- `architecture_transformation`: one tenant-bound link from an `architecture_scenario` with an immutable baseline to a `remediation_initiative`, plus transformation identity, valid interval, system recording/supersession interval, truth status, and evidence.
- `transformation_history_record`: append-only ordered state history with `effective_at`, independent `recorded_at`, actor reference, decision reason, truth status, and evidence.
- `project_transformation_state(uuid,timestamptz,timestamptz)`: tenant-bound projection of the latest transformation state visible at both a real-world valid-time cutoff and a system-recording cutoff.

A transformation cannot target an inactive scenario or initiative, its valid interval must be contained in both parent intervals, the scenario target instant must lie inside the transformation interval, and the scenario must already have its immutable baseline. Current authoritative transformations with the same code cannot overlap.

History begins with `proposed` sequence 1. The database permits only `proposed -> approved|rejected`, `approved -> started|cancelled`, and `started -> completed|cancelled`. Approval, cancellation, and rejection require authoritative truth; started and completed states require authoritative or observed truth. Authoritative and observed facts require evidence, so proposed or inferred automation output cannot silently become an approved architecture decision.

Real-world and system time remain distinct. A future-effective approval may be recorded before its `effective_at`; there is deliberately no `recorded_at >= effective_at` constraint. Sequence history itself stays deterministic: sequence numbers are contiguous and neither effective nor recording order may move backward within one transformation stream. The projector independently applies the requested valid-time and recorded-time cutoffs.

Transformation meaning is immutable after insertion except for one-time supersession, while history rows reject update and delete operations. Forced RLS and composite tenant foreign keys preserve tenant isolation. `decision_actor_ref` is an auditable identity reference, not a replacement for Keyverse authorization. Project tasks, staffing, sprint state, deployment telemetry, and external execution-system state remain outside this model.

## Technology change impact projection

Migration 0015 adds the first buyer-facing Technology Change Impact & Target-State Planner query without introducing another write model:

- `project_technology_change_impact(uuid,timestamptz,timestamptz,integer)`: starts from one tenant-owned `technology_version`, resolves its owning technology component through `has_version`, finds affected applications through `uses_technology`, then finds supported business capabilities through `supports_capability`.

Every traversed relation is evaluated independently at the requested valid-time and recorded-time cutoffs. A relation must already have been recorded, must still be visible at the requested system time, must contain the requested real-world time, and cannot have `superseded` or `rejected` truth origin. The lifecycle phase is selected under the same two-time rule. This lets an audit query reproduce what the system actually knew at an earlier cutoff even when capability evidence was backfilled later.

The projection returns the IDs and business codes needed to explain the path, support-end date and lifecycle phase, relation truth statuses, relation/lifecycle evidence IDs, and three deterministic decision fields. `impact_status_code` classifies current support/lifecycle risk; `evidence_state_code` makes incomplete capability or support evidence explicit; `recommended_action_code` tells the caller whether to monitor, plan a target state, start remediation, or complete missing evidence. Evidence gaps take precedence over a remediation recommendation so incomplete architecture knowledge cannot masquerade as a precise decision.

The caller chooses a planning horizon between 1 and 3650 days. An unknown technology version or out-of-range horizon fails closed. The function is read-only and never creates or approves scenarios, initiatives, or transformations, and it never promotes inferred/proposed evidence into authority.

This slice intentionally stops at EA-owned capability impact. Physical schema/design evidence remains owned by pg-erd-cloud; catalog assets, data products, dashboards/models/AI projections and governed lineage remain owned by Semantic Data Portal; inferred lineage remains owned by LineageWeave. Those products can later enrich this impact path through their published contracts/events without direct cross-service application-table SQL or duplicated authority.

## Integration

- `outbox_event` provides atomic publication and object-shaped JSON payloads.
- `projection_receipt` makes inbound event replay idempotent and validates authority URI plus UUIDv7 event identity.
- `evidence_record` stores opaque, tenant-consistent evidence references and byte digests.
- `identity_link` stores Keyverse subject links, not credentials.

Operational event timestamps preserve system-time causality: an outbox event cannot be marked published before `recorded_at`, and an inbound projection cannot be marked processed before `received_at`. These invariants are exercised on clean installation and migration upgrade paths. Service-to-service direct application-table SQL is not an integration contract.
