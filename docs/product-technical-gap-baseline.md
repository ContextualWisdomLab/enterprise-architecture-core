# Product and technical gap baseline

Status: Proposed  
Assessment date: 2026-09-27

## Evidence boundary

- Protected base: `develop@dd71e40a86385fb7861b0f1be19891a3f3e29ece`
- Source reviewed before this repair: `906e9896196062fccdf636d128fc77833280479e`
- RED documentation contract: `91166b2d0f7c8b901f9ab7a6669dd14ad95f73d2` (`25` failures)
- Writer lane: [pull request #51](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/51)

This baseline describes source evidence, not a release, deployment, accepted decision, or license grant.

## Goal

Provide a reconstructable enterprise Context Map and architecture-decision authority while leaving product-domain truth, runtime ownership, data, APIs, operations, and releases with their canonical product contexts.

## Context Map

| Context | Responsibility | Relationship |
| --- | --- | --- |
| `enterprise-architecture-core` | Enterprise Context Map and cross-context decisions | Publishes reviewed decisions; does not own product domain truth or runtime control. |
| Product contexts | Ubiquitous Language, aggregates, APIs, persistence, operations, and releases | Consume accepted decisions and versioned contracts through anti-corruption layers. |
| Optional shared services | Repeated responsibility behind independently deployed, versioned contracts | Remain optional until their protected-branch evidence and immutable release exist. |
| `.github` | Reusable CI, security, review, and release governance | Supplies governance contracts without becoming the architecture authority. |

## Artifact baseline

| Artifact | Status | Evidence and Action |
| --- | --- | --- |
| PRD | Missing | Define users, decision workflow, acceptance criteria, and non-goals on the canonical writer lane. |
| TRD | Missing | Define the versioned decision schema, validation, publication, and consumer contract after the PRD. |
| ADR | Missing | Create reconstructable records covering problem, constraints, alternatives, evidence, risks, effects, and follow-up. Current prose is not an Accepted ADR set. |
| UML | Missing | Add only when component or sequence relationships need a maintained formal view. |
| ERD | Not applicable yet | Reassess when persistent storage is selected; no database is evidenced in the reviewed source. |
| Architecture | Partial | README and public overview define responsibility and boundaries, but no released decision contract exists. |

## Gap register

| Gap | Action | Status |
| --- | --- | --- |
| No canonical versioned decision schema or API | Define it in the TRD, add fixtures and conformance tests, then publish an immutable version. | Proposed |
| No protected, accepted enterprise Context Map artifact | Review owner and relationship evidence before protected-branch integration. | Proposed |
| No reconstructable ADR set | Add numbered Proposed ADRs and promote each only after evidence and review. | Proposed |
| No repository `LICENSE`, provenance inventory, SBOM, NOTICE, or third-party attribution | Verify ownership and inbound obligations; select a compatible grant only when rights are established. | Blocked on evidence |
| No verified GitHub Pages publication | Keep Pages wording source-only until an actual deployment and HTTP endpoint are verified. | Proposed |
| No release or package metadata | Bind source, contract, SBOM, provenance, and changelog to the same immutable Release. | Proposed |
| No security or operations acceptance evidence | Define threat, recovery, support, and failure-handling evidence appropriate to the eventual delivery model. | Proposed |

## Release, License, and Pages acceptance

A Release is valid only when its protected source revision, versioned decision contract, tests, changelog, SBOM, provenance, license decision, and required attribution are bound to the same immutable version. A public repository or pull request is not a release.

License rights must be verified rather than inferred. Until a repository-level grant exists, reuse is not authorized by this documentation.

Pages source configuration and actual publication are separate facts. GitHub Pages must not be described as live until deployment evidence and the public endpoint are verified.
