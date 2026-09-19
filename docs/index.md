---
title: Enterprise Architecture Core
---

# Enterprise Architecture Core

Enterprise Architecture Core is the authoritative decision plane for ContextualWisdomLab-wide architecture and transformation.

It helps product teams, operators, and reviewers answer four practical questions:

1. Which bounded context owns a capability or fact?
2. How may another context consume it?
3. Which architectural decision introduced the relationship?
4. What evidence, risk, and follow-up keep that decision valid?

## What belongs here

- Enterprise Context Maps and cross-context relationship decisions
- Architecture and transformation decision records
- Ownership, dependency, and anti-corruption boundaries
- Evidence and follow-up needed to reconstruct or revise a decision

## What stays with products

Product repositories retain domain truth, Ubiquitous Language, aggregates, persistence, APIs, operations, and releases. Shared control planes and libraries remain optional integrations behind versioned contracts.

## Explore

- [Repository](https://github.com/ContextualWisdomLab/enterprise-architecture-core)
- [README](https://github.com/ContextualWisdomLab/enterprise-architecture-core/blob/develop/README.md)
- [Architecture decisions](https://github.com/ContextualWisdomLab/enterprise-architecture-core/tree/develop/docs)
- [Ask DeepWiki](https://deepwiki.com/ContextualWisdomLab/enterprise-architecture-core)

Protected default-branch source is authoritative. A proposal or pull request is not an accepted enterprise decision until its review and integration are complete.
