# Enterprise Architecture Core

Enterprise Architecture Core is the ContextualWisdomLab enterprise architecture decision plane for governed target-state, capability, transformation, and architecture-description decisions.

## Product responsibility

This repository owns architecture descriptions, target-state and capability decisions, transformation decisions, and the contracts that expose those decisions to other products. It keeps foreign product systems authoritative for their own operational data and stores bounded references and decision evidence rather than reading or rewriting sibling application tables.

The current documentation stack is under active governance and branch migration. This site source must not be used to infer a production deployment, released runtime, certification, or current protected-branch topology that has not been verified live.

## Start here

- [Repository README](../README.md) — product boundary, authority map, and supported composition model.
- [Product and technical gap baseline](product-technical-gap-baseline.md) — current evidence-backed gaps and remediation state.
- [Architecture decisions](adr/) — accepted architecture, transformation, and composition decisions.
- [Standards references](REFERENCES.md) — verified bibliography and standards evidence.
- [GitHub Releases](https://github.com/ContextualWisdomLab/enterprise-architecture-core/releases) — immutable release artifacts when available.
- [Ask DeepWiki](https://deepwiki.com/ContextualWisdomLab/enterprise-architecture-core) — repository-aware navigation and questions.

## Ecosystem boundary

Orgmetra remains authoritative for people and employment truth; fast-mlsirm remains authoritative for psychometric numerical kernels; data, schema, lineage, orchestration, and other Context Fabric products remain independently authoritative behind explicit contracts. Enterprise Architecture Core consumes those products through published contract/evidence boundaries and owns only the architecture and transformation decisions that belong here.

## Verification and publication

Repository-facing claims require current protected integration and live evidence. Branch-only documentation, queued checks, draft stacks, or predecessor evidence are not shipped truth. This file is a GitHub Pages source prerequisite, not proof that Pages is live. Pages publication is complete only after the reviewed source reaches the protected default branch, the organization-owned metadata reconciler applies the intended Pages configuration, deployment succeeds, and the public HTTPS content is re-read successfully.
