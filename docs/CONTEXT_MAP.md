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

### Strategy & Transformation

Owns objectives, initiatives, milestones and approved transformation history. Application services orchestrate commands; domain invariants remain independent of transport/provider DTOs. Transactional outbox records domain events atomically with state changes.

### Scenario Planning

Owns immutable baselines and ordered deltas. A scenario is a candidate state, not automatically authoritative production architecture. Approval/execution is an explicit state transition through the owning strategy/transformation boundary.

### Cross-Domain Evidence Projection

Owns only the receipt, normalization and bitemporal projection needed for EA decisions. It must preserve the upstream owner, source identity, truth origin and receipt/provenance. It may not recreate the full foreign product model or write directly to another product's application tables.

### Target-State Planner

Joins EA-owned architecture facts with accepted cross-domain evidence to answer: what changed, what is affected, what should be remediated next, what target state is proposed, and what approved transformation records the decision. Planner proposals remain proposed until the explicit approval/transition boundary succeeds.

## External Context Map

| External context | Relationship | Boundary rule |
| --- | --- | --- |
| `context-graph-contracts` | Published Shared Kernel / upstream contract provider | EA consumes the immutable provider-neutral contract and uses an Anti-Corruption Layer for EA-specific semantics. Shared contract types do not own EA aggregates. |
| Data/AI Context (`semantic-data-portal`) | Upstream evidence provider | The portal remains system of record for catalog assets, glossary, lineage, domains, data products, output ports, contracts and trust/certification. EA stores only the minimum receipt-bound projection required for an architecture decision. |
| Physical Schema Evidence (`pg-erd-cloud`) | Upstream evidence provider | Physical schema/design facts remain owned there. EA may reference accepted evidence; it must not become a physical schema editor or duplicate that source of truth. |
| Inferred Lineage (`LineageWeave`) | Upstream proposed/inferred evidence provider | Inferred lineage remains inferred/proposed unless an authoritative owner explicitly accepts it. EA must preserve origin and may not silently promote it. |
| Orchestration (`contextual-orchestrator`) | Proposal-producing client | Orchestration may call EA commands through the public application/API boundary but may not directly mutate EA tables or change policy through prompt output. |
| Naruon / buyer-facing clients | Downstream client | Presentation/search/assistant concerns remain outside the decision-plane domain. Clients consume stable APIs/events and accessible evidence views. |

## Dependency rules

Domain rules must not depend on HTTP, framework, ORM or provider SDK DTOs. Application services may orchestrate repositories, authorization ports and event publication, but domain invariants belong to the domain model/database invariant where the transaction is authoritative. Adapters translate through explicit ports or Anti-Corruption Layers. Direct cross-service application-table SQL is prohibited.

The current `src/ea_core_foundation` package predates this bounded-context decomposition and is tracked as open DDD debt rather than being relabeled as compliant. `docs/product-technical-gap-baseline.md` records the correction sequence and the architecture-fitness test prevents new generic buckets or direct foreign implementation dependencies while that migration is planned.

## Integration governance

The intended integration/default branch is `main`. Repository metadata still reports `develop` while root integration work targets `main`, and `main` is currently unprotected. Central governance must make `main` a protected coherent integration/default target before this stack is migrated or released. Existing protected branches are not weakened as a shortcut.
