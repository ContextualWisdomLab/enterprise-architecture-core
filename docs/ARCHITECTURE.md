# Architecture

## Bounded contexts

```text
Keyverse
   │ OIDC identity
   ▼
Enterprise Architecture Core
   │ authoritative architecture decisions / public events
   ├────────────► Semantic Data Portal / shared graph projection
   │
   ├◄──────────── pg-erd-cloud observed schema evidence
   ├◄──────────── LineageWeave inferred relation proposals
   ├◄──────────── Noema deployable/runtime architecture context
   │
   └◄──────────── Quarantine Sandbox Runtime architecture context
                    ▲                       ▲
                    │ application-service   │ artifact-analysis
                    │ lease                 │ evidence
          contextual-orchestrator         Wardnet
```

The diagram is a responsibility map, not a claim of a shared database or direct runtime dependency. Every cross-product exchange uses a released versioned package/API/event contract or a product-owned Anti-Corruption Layer.

## Ownership

Enterprise Architecture Core owns:

- business capability;
- application and application interface;
- technology component, version, provider, and lifecycle;
- enterprise architecture relationship;
- versioned portfolio assessment;
- objective, initiative, scenario, and transformation decision.

It does not own datasets, columns, data contracts, physical schema snapshots,
inferred narrative lineage, credentials, hostile-workload sandbox lifecycle,
Agent tasks/results/reasoning, workflow execution state, checkpoint content,
malware verdicts, artifact risk scores, SOC incidents, or project execution status.

Noema independently owns Agent Runtime, Workflow/Task Execution, Tool/Capability boundaries, State/Checkpoint, Isolation Integration, Policy/Approval, Observability and Recovery. EA may project only Noema deployable/runtime/service/API/worker capability identity; database/queue/object-storage/runtime technology; provider/version; lifecycle; ownership; architecture-risk context; remediation and transformation after released Context Graph admission. Tool payloads, workflow state, approvals, checkpoints, prompts, model outputs and user business data remain Noema truth and cannot become authoritative EA facts by ingestion.

Quarantine Sandbox Runtime independently owns reusable hostile-workload sandbox lifecycle, resource enforcement, cleanup, attestation and artifact-analysis evidence. `contextual-orchestrator` owns Chat/Agent/task/tool caller policy, authorization, application selection, secrets and user-visible actions when requesting application-service leases. Wardnet owns maliciousness verdict, incident and quarantine/block/notification/retention policy when consuming artifact-analysis evidence. EA may project only architecture-relevant runtime, application-service, API and backend identity; container-runtime/security technology, provider and version; lifecycle, architecture-risk context, ownership, remediation/transformation and attestation provenance, with source truth and bitemporal provenance preserved. A projection category does not assert that a producer API or backend capability exists: only released CGC-compatible producer evidence may instantiate those architecture facts.

## Write and read models

The canonical write model is normalized PostgreSQL. Inventory objects do not
carry duplicated portfolio scores: framework/version, scale/value, dimension,
cycle, and object-assessment meaning are normalized and joined at the
transactional boundary. Commands update business facts and insert outbox events
atomically. Consumers build graph, search, matrix, or analytics projections from
the events. A projection can be deleted and rebuilt without changing
authoritative history.

Append-only evidence, inbound receipts, outbox events, and transformation
history expose the same deterministic tenant-derived 16-bucket routing
contract. Their hot-write indexes and storage headroom prepare a future
partition cutover without making the current service depend on physical
partition names or weakening tenant isolation.

No connector may read another product's application tables or vendor-copy its source model. Foreign evidence is represented by canonical/source references, truth status, effective/system time and provenance through the accepted Context Graph release contract.

## Temporal and truth semantics

Object revisions, relationships, identity links, lifecycle intervals,
assessment frameworks/cycles, and object assessments carry real-world validity
and system recording semantics. Queries may therefore ask both what was valid
at a date and what the system knew at a historical cutoff. Assessment truth
uses the same explicit origin vocabulary as architecture assertions:
authoritative or observed scores require evidence, while inferred/proposed
scores remain reviewable without silently becoming authoritative.

Runtime/security evidence follows the same rule. Noema runtime/workflow/model output and quarantine attestation/artifact-analysis results can support an EA architecture-risk decision only through the bounded released projection. Neither transport admission nor a foreign runtime-produced result becomes authoritative EA truth automatically. Wardnet's verdict authority also remains outside EA.

## Process surface

The installable process binds `0.0.0.0:$PORT` and implements `GET /health`
then `GET /ready`. Domain commands stay unpublished until a purpose-bound
Keyverse boundary exists. Neighbor systems connect through
`contracts/connectors/ecosystem.json`.

## Scenario direction

A future target state is represented as an immutable baseline plus ordered
scenario changes. Draft scenarios never mutate current authoritative state.
Execution closes old intervals and creates new facts through normal commands.
