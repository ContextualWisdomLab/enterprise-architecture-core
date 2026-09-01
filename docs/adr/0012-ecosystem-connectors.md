# ADR 0012: Connect Neighbor Systems Through Contracts, Not SQL

- **Status:** Accepted
- **Date:** 2026-08-16
- **Updated:** 2026-09-01

## Decision

CWL products remain independently authoritative and integrate with the Enterprise Architecture Decision Plane only through explicit versioned package, API, event, evidence, or Anti-Corruption Layer boundaries. `contracts/connectors/ecosystem.json` is the executable Context Map inventory for those boundaries. Direct cross-service application-table SQL and source copying are prohibited.

`context-graph-contracts` is the provider-neutral Shared Kernel used for Context Assertion, CloudEvent, canonical reference, truth, bitemporal, and provenance semantics. A Context Graph receipt or admission result proves contract compatibility/evidence identity; it is not foreign-product authority and does not authorize EA state changes by itself.

The Quarantine Sandbox Runtime is an independently deployable reusable hostile-workload isolation runtime. It owns sandbox lifecycle/resource enforcement/cleanup/attestation and artifact-analysis evidence. `contextual-orchestrator` remains the caller-policy owner for Chat/Agent/task/tool authorization, application selection, secrets, and user-visible actions; it may call the runtime application-service lease capability. Wardnet remains the SOC/gateway owner for maliciousness verdicts, incidents, quarantine/block/notification/retention; it may call the runtime artifact-analysis/evidence capability. EA may receive only architecture-relevant runtime/backend technology, provider/version, lifecycle, architecture-risk context, ownership, remediation/transformation, and attestation provenance through a released compatible Context Graph contract. Malware verdicts and artifact risk scores are forbidden as authoritative EA architecture facts.

Inferred LineageWeave relations, scanner/security findings, model-generated proposals, and other foreign observations retain their source truth status until an explicit EA-owned command accepts an architecture decision. No connector is allowed to turn transport receipt, scanner output, runtime evidence, or model output into an authoritative EA fact by ingestion alone.

## Consequence

EA Core can be deployed independently and projects only the minimum architecture context required for a decision. Foreign products retain their own source of truth, storage, runtime and policy responsibilities. Connector admission fails closed when a required owner, reuse/deployment boundary, Context Graph release binding, preserved semantics, or directional interaction is absent.
