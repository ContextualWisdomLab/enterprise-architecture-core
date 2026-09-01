# Enterprise Architecture Core

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ContextualWisdomLab/enterprise-architecture-core)

Enterprise Architecture Core is ContextualWisdomLab’s **enterprise architecture decision plane**. Buyers and operators use it to record target-state, capability, and transformation decisions, and to publish the contracts other hosts call. It is independently operable. Hosts consume what this repository publishes. They do not check out sibling CWL repositories to reconstruct the plane.

The plane describes architecture. It does not become the system of record for employment or psychometric computation.

## What this plane decides

This repository owns architecture-description and transformation-decision records for the CWL enterprise:

- architecture descriptions and the viewpoints that make those descriptions usable
- target-state, capability, and transformation decision records
- published contracts that hosts call without sharing application tables

It does **not** own:

- employment, organization, job, position, assignment, or hire-to-assignment truth — that remains [Orgmetra](https://github.com/ContextualWisdomLab/Orgmetra)
- psychometric numerical kernels, item-response estimation, or recovery diagnostics — that remains [fast-mlsirm](https://github.com/ContextualWisdomLab/fast-mlsirm)

Foreign systems stay authoritative for their own catalogs. This plane stores decision records and canonical references. It does not open another product’s application tables.

## Use it independently

The CWL microservices rule is **따로 또 같이**: each product runs and is callable on its own, and allowed hubs may compose it.

Operators treat this repository as a complete product boundary:

1. Read the authority map and accepted decisions in this repository.
2. Deploy and call this service from its own published surface when a runtime is released from this repository.
3. Consume versioned contracts published here. Do not vendor sibling source trees, Git submodules, or monorepo checkouts to obtain those contracts.

The protected `develop` baseline currently publishes the buyer and operator contract for the plane: this README, the architecture-decision records, and the standards bibliography. Machine-readable API, event, and schema contracts will be published from this same repository when they exist. Until then, the independent unit of consumption is this repository’s published documentation. This baseline does not ship an application package or test harness.

## How hosts consume published contracts

A host — another CWL product, a customer integration, or a composition hub — consumes **published artifacts from this repository**, not a sibling working tree.

| Host need | Consume from this repository | Do not do |
| --- | --- | --- |
| Understand the plane | This README and `docs/adr/` | Infer ownership from another product’s schema |
| Call the plane | Versioned contracts published here (when released) | Check out Orgmetra, fast-mlsirm, Naruon, gyeot, or other siblings to copy internals |
| Keep foreign truth intact | Canonical references and decision receipts | Read or write another service’s application tables |
| Compose a workspace | Hub-side wiring in the hub’s own repository | Fold this plane into a hub repo |

When machine-readable contracts are published, copy or fetch those artifacts (for example a versioned OpenAPI, AsyncAPI, or JSON Schema file released from this repository). Do not reconstruct the contract by browsing sibling source.

## Composition hubs

Leaf products stay independently deployable. Composition hubs call them as published dependencies. That hub-and-leaf call is the supported MSA path — **따로 또 같이** — not a reason to merge repositories.

| Hub | Role | How it uses this plane |
| --- | --- | --- |
| [Naruon](https://github.com/ContextualWisdomLab/naruon) | Customer-owned mail, calendar, and file control plane; judgments and decisions | May compose this plane through published contracts when a workspace needs architecture or transformation decisions. Naruon wiring lives in Naruon’s own repository. |
| [gyeot (곁)](https://github.com/ContextualWisdomLab/gyeot) | On-device wellness composition hub | May compose this plane through the same published contracts when a host needs architecture-decision context. Gyeot wiring lives in gyeot’s own repository. |

Naruon and gyeot are allowed composition hubs. Those links are supported. They do not make this plane a module inside either hub, and they do not require this repository to check those hubs out.

## Authority boundaries

```text
Orgmetra                 -> employment truth
fast-mlsirm              -> psychometric numerical kernels
Enterprise Architecture Core
  -> architecture descriptions
  -> target-state / capability / transformation decisions
  -> published host contracts
Naruon / gyeot           -> optional composition hubs
```

- **Orgmetra** owns people, employment, organization, jobs, positions, assignments, and evidence-backed talent decisions. This plane may reference those records. It does not replace them.
- **fast-mlsirm** owns MLSIRM/MLS2PLM numerical kernels, fitting, and recovery diagnostics. This plane may consume published measurement artifacts. It does not reimplement those kernels.
- **This plane** owns architecture-description and transformation-decision records, and the contracts hosts use to call them.

## Documentation

| Topic | Document |
| --- | --- |
| Product and technical gap baseline | [docs/product-technical-gap-baseline.md](docs/product-technical-gap-baseline.md) |
| Architecture-description boundary (ISO/IEC/IEEE 42010:2022) | [docs/adr/0001-architecture-description-boundary.md](docs/adr/0001-architecture-description-boundary.md) |
| Target-state, capability, and transformation records (TOGAF Standard) | [docs/adr/0002-target-state-capability-transformation.md](docs/adr/0002-target-state-capability-transformation.md) |
| Viewpoint language (ArchiMate 4) | [docs/adr/0003-archimate-viewpoint-language.md](docs/adr/0003-archimate-viewpoint-language.md) |
| CWL MSA and composition-hub rule | [docs/adr/0004-cwl-msa-composition-hubs.md](docs/adr/0004-cwl-msa-composition-hubs.md) |
| ADR index | [docs/adr/README.md](docs/adr/README.md) |
| Verified standards bibliography (APA 7th) | [docs/REFERENCES.md](docs/REFERENCES.md) |
