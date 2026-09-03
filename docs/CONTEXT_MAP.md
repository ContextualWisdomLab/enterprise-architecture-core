# Context Map

`enterprise-architecture-core` is the authoritative Enterprise Architecture Decision Plane. It owns decisions about the enterprise architecture portfolio and the evidence-backed state transitions needed to plan and govern target state. It is not the organization-wide data catalog, a physical-schema design tool, an inferred-lineage engine or an autonomous orchestration authority.

## Subdomain classification

| Subdomain | Classification | Responsibility |
| --- | --- | --- |
| Enterprise Architecture Decision Plane | Core | Business capabilities, applications, interfaces, technology components/versions/providers, organization context, typed temporal relations and lifecycle. |
| Portfolio Assessment | Core | Versioned assessments and decision-facing portfolio views derived from owned EA facts and receipt-bound evidence. |
| Strategy and Transformation | Core | Objectives, initiatives, milestones, transformation history and approved architecture change. |
| Scenario Planning | Core | Immutable scenario baselines, ordered deltas, deterministic projection and comparison of candidate target states. |
| Technology Change Impact & Target-State Planner | Core | Trace technology lifecycle/EOL impact through applications/capabilities and accepted cross-domain evidence to remediation initiatives, target-state plans and approved transformation history. |
| Cross-Domain Evidence Projection | Supporting | Tenant-safe, receipt-bound projection of evidence owned by other products. Projection is not ownership transfer. |
| Identity / authorization adapter | Generic | Keyverse/OIDC verification, authenticated tenant/role binding and runtime authorization ports. Caller-set tenant context is filtering context, not authorization by itself. |
| Persistence / migration / outbox-inbox plumbing | Generic | PostgreSQL migration ledger, RLS, transactional outbox/inbox, replay/idempotency and operational evidence. These mechanisms serve the domain; they do not define business truth. |

## Internal bounded contexts

### Architecture Inventory

Owns the EA identity and lifecycle of capabilities, applications, interfaces, technology inventory, organizations and typed relations. Aggregate invariants include tenant-safe identity, canonical references, temporal validity and explicit truth origin for evidence-backed relations.

### Portfolio Assessment

Owns assessment versions and decision-facing portfolio conclusions. Assessment input may reference evidence from other contexts, but the assessment decision and its version history are EA facts.

The current bounded owner path is `src/ea_core_foundation/portfolio_assessment/`. Portfolio assessment read/summary behavior lives in `portfolio_assessment.py`; EA-owned Data/AI assessment reassessment commands and their follow-up status read live in `data_management_recheck.py` and `data_management_recheck_status.py`. The historical root modules remain behavior-free compatibility facades during consumer migration; they do not define a second bounded context or authority. Runtime composition uses these owner modules directly where the migration has been proven in the active stack; foreign evidence validation remains outside this Core context.

### Strategy & Transformation

Owns objectives, initiatives, milestones and approved transformation history. Application services orchestrate commands; domain invariants remain independent of transport/provider DTOs. Transactional outbox records domain events atomically with state changes.

The bounded owner path is `src/ea_core_foundation/strategy_transformation/`. Transformation scheduling, start, completion, target-state verification and governed replanning command behavior lives in `strategy_transformation/schedule.py`, `strategy_transformation/start.py`, `strategy_transformation/complete.py`, `strategy_transformation/verify.py` and `strategy_transformation/replan.py`; target-state monitoring freshness/read behavior lives in `strategy_transformation/monitor.py`. Historical root `start.py`, `complete.py`, `verify.py`, `replan.py` and `monitor.py` modules are behavior-free compatibility facades preserving the same public objects while consumers migrate. The deployable `runtime.py` now imports the schedule/start owners directly and re-exports the existing scheduling API objects; `completion_runtime.py`, `verification_runtime.py`, `monitoring_runtime.py` and `replan_runtime.py` likewise compose the moved Strategy & Transformation ports directly instead of routing internal calls through historical facades.

These path moves do not transfer authorization or persistence authority. Scheduling, start, completion, verification and replanning remain EA-owned tenant-scoped stored commands with idempotent receipts and transactional outbox semantics; monitoring remains a purpose-authorized tenant-bound read through the EA-owned PostgreSQL query port with separate valid/business and recorded/system cutoffs. Replanning creates a governed replacement proposal without rewriting the gap-detected predecessor. Runtime composition consumes the Generic Identity & Authorization adapter and the responsibility-named `decision_plane_http.py` application/HTTP port directly for the portions already migrated; compatibility roots remain migration surfaces, not new bounded contexts.

### Scenario Planning

Owns immutable baselines and ordered deltas. A scenario is a candidate state, not automatically authoritative production architecture. Approval/execution is an explicit state transition through the owning strategy/transformation boundary.

### Cross-Domain Evidence Projection

Owns only the receipt, normalization and bitemporal projection needed for EA decisions. It must preserve the upstream owner, source identity, truth origin, effective/system time and receipt/provenance. It may not recreate the full foreign product model or write directly to another product's application tables.

For admitted Context Assertion CloudEvents, the receipt contract is stricter than payload projection alone: EA retains source authority; CloudEvent `id`, `source`, `type`, `subject`, `time` and `dataschema` identity; the exact admitted schema/profile/admission versions; and provenance. A projection that cannot identify the exact admitted message and compatibility contract is invalid evidence, even when its normalized EA fields are otherwise well formed.

Connector ownership/release-binding validation lives in `src/ea_core_foundation/cross_domain_evidence/connector_catalog.py`. Foreign Data/AI reassessment-status contract validation lives in `cross_domain_evidence/data_management_recheck_status.py`. Their historical `validation_*` import paths are retained only as behavior-free compatibility facades. EA-owned reassessment decisions stay in Portfolio Assessment rather than being absorbed into this Supporting context.

### Identity & Authorization Adapter

This Generic context verifies Keyverse/OIDC bearer identity and binds authenticated tenant/role/subject context for EA application ports. It does not own architecture facts, business authorization policy outside the EA runtime boundary, or caller-supplied tenant truth. Provider-facing verification behavior lives under `src/ea_core_foundation/identity_authorization/authorization.py`; the historical root `authorization.py` remains a behavior-free compatibility facade that resolves to the same module object while internal and external imports migrate. Core and Supporting contexts consume the verified authorization context/ports rather than becoming identity providers themselves.

### Target-State Planner

Joins EA-owned architecture facts with accepted cross-domain evidence to answer: what changed, what is affected, what should be remediated next, what target state is proposed, and what approved transformation records the decision. Planner proposals remain proposed until the explicit approval/transition boundary succeeds.

## External Context Map

All foreign product facts enter through released versioned `context-graph-contracts` assertions/events or another explicit versioned public contract. EA stores the minimum architecture projection needed for a decision and never treats receipt, transport or a foreign observation as authority transfer.

| External context | Relationship | Boundary rule |
| --- | --- | --- |
| `context-graph-contracts` | Published Shared Kernel / upstream contract provider | EA consumes the immutable provider-neutral contract and uses an Anti-Corruption Layer for EA-specific semantics. Shared contract types do not own EA aggregates. |
| Data/AI Context (`semantic-data-portal`) | Upstream architecture/evidence projection | The portal remains system of record for catalog assets, glossary, lineage, domains, data products, output ports, contracts and trust/certification. EA keeps only canonical references and receipt-bound projection needed for an architecture decision. |
| Physical Schema Evidence (`pg-erd-cloud`) | Upstream evidence provider | Physical schema/design facts remain owned there. EA may reference accepted evidence; it must not become a physical schema editor or duplicate that source of truth. |
| Inferred Lineage (`LineageWeave`) | Upstream proposed/inferred evidence provider | Inferred lineage remains inferred/proposed unless an authoritative owner explicitly accepts it. EA must preserve origin and may not silently promote it. |
| Orchestration (`contextual-orchestrator`) | Upstream proposal producer + command client | Orchestration may project proposed/inferred architecture context and call authorized EA commands, but prompt/model output cannot directly mutate EA tables or become authoritative architecture truth. Orchestrator also remains the caller-policy owner when it requests application-service leases from Quarantine Sandbox Runtime. |
| Quarantine Sandbox Runtime (`quarantine-sandbox-runtime`) | Independent reusable isolation runtime + evidence provider | The runtime owns hostile-workload sandbox lifecycle/resource enforcement/cleanup/attestation and artifact-analysis evidence. `contextual-orchestrator` calls the application-service lease capability; Wardnet calls artifact-analysis/evidence. EA may project runtime/backend identity, technology/provider/version, lifecycle, architecture-risk context, ownership, remediation/transformation and attestation provenance only through a released compatible Context Graph contract. Malware verdicts and artifact risk scores are never authoritative EA facts. No source copy or direct DB access is allowed. |
| Naruon | Upstream product-context projection + downstream client | Naruon remains authoritative for its workspace/product runtime facts. Deployable/API/provider/version/lifecycle/risk changes may project into EA; EA architecture/lifecycle events may flow back through public events without cross-service SQL. |
| BandScope (`bandscope`) | Upstream product-context projection | BandScope remains authoritative for its runtime/product facts. EA receives only canonical deployable/API/provider/version/lifecycle/risk projections with source provenance. |
| Organization context (`Orgmetra`) | Upstream bounded organization/product projection | Project only organization/deployable references required for EA decisions. Employee, HR and assessment records remain in Orgmetra and are not copied into the EA store. |
| Learning/research platform (`TEPP`) | Upstream product-context projection | Project architecture-relevant service/package/API/database/provider/version/lifecycle/risk changes. Learning/research facts remain authoritative in TEPP. |
| Security posture (`wardnet`, `appguardrail`) | Upstream observed security evidence | Findings may influence architecture risk/impact decisions only with preserved source, truth status, effective/system time and provenance. Scanner/detection output is not silently promoted to authoritative architecture truth. Wardnet additionally owns maliciousness verdict, incident and quarantine/block/notification/retention policy even when it consumes Quarantine Sandbox Runtime analysis evidence. |
| Governance/Risk/Compliance (`governance-risk-compliance`) | Upstream control/risk evidence | EA references control, risk and evidence needed for architecture decisions; compliance records and attestations remain authoritative in the GRC product. |

## Dependency rules

Domain rules must not depend on HTTP, framework, ORM or provider SDK DTOs. Application services may orchestrate repositories, authorization ports and event publication, but domain invariants belong to the domain model/database invariant where the transaction is authoritative. Adapters translate through explicit ports or Anti-Corruption Layers. Direct cross-service application-table SQL is prohibited.

The current `src/ea_core_foundation` package predates this bounded-context decomposition and remains open DDD debt rather than being relabeled as compliant. Mapped slices now include the Cross-Domain Evidence connector/foreign-contract validators, the Core Portfolio Assessment read/reassessment ports, the Core Strategy & Transformation scheduling/start/completion/verification/replanning/target-state monitoring ports, and the Generic Identity & Authorization adapter. Historical imports for moved standalone modules are compatibility-only and architecture-fitness regressions prevent executable behavior from returning to them. Runtime composition in the active stack now consumes canonical bounded owners directly where covered by fitness tests. The package-level debt is not closed by these moves; `runtime.py` still owns deployable HTTP composition, `decision_plane_http.py` remains broad, and other feature-specific validation/application modules still require responsibility proof before any further move. `docs/product-technical-gap-baseline.md` records the remaining sequence and tests prevent new generic buckets or direct foreign implementation dependencies.

## Integration governance

The intended integration/default branch is `main`. Repository metadata still reports `develop` while root integration work targets `main`, and `main` is currently unprotected. Central governance must make `main` a protected coherent integration/default target before this stack is migrated or released. Existing protected branches are not weakened as a shortcut.
