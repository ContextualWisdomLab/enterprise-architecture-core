# Enterprise Architecture Core

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ContextualWisdomLab/enterprise-architecture-core)

**The authoritative enterprise architecture and transformation decision plane for the ContextualWisdomLab ecosystem.**

Enterprise Architecture Core records how bounded contexts relate, where authority lives, and which transformation decisions apply across products. It provides durable context maps and decision evidence without taking domain truth, runtime control, or deployment ownership away from product repositories.

## Responsibility

- Maintain the enterprise Context Map and cross-context relationship decisions.
- Record architecture and transformation decisions with constraints, alternatives, evidence, risks, effects, and follow-up.
- Make ownership, upstream/downstream dependency, and anti-corruption boundaries visible to product teams and operators.
- Preserve decision history so a new contributor can reconstruct why the current architecture exists.

## Boundary

Product repositories retain their Ubiquitous Language, domain rules, aggregates, data ownership, and release authority. Shared services and libraries are optional integrations behind versioned contracts; this repository does not turn an architectural decision into mandatory runtime infrastructure.

Open proposals remain proposals until their evidence, review, and protected-branch integration are complete.

## Public overview

The concise buyer- and operator-facing overview is maintained in [docs/index.md](docs/index.md). Protected default-branch content remains authoritative.
