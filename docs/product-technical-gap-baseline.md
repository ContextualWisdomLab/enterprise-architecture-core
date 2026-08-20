# Product and technical gap baseline

**Snapshot:** 2026-08-20, GitHub API and repository inspection  
**Repository:** `ContextualWisdomLab/enterprise-architecture-core`  
**Decision record:** [ADR 0005](adr/0005-product-technical-gap-baseline.md)

This is an evidence snapshot, not a claim that every open branch is shipped.
Refresh it after a merge, base-branch change, release, failed check, or
material runtime change. The customer action in each row is the acceptance
test for the next loop.

## Executive decision

The product has a credible headless decision-plane foundation and a growing
authenticated transformation decision surface. The buyer-facing blocker is
delivery truth: the protected default branch is still the initialization
baseline while the deployable runtime and later decision capabilities exist on
`main` and stacked pull requests. There is no GitHub release or version tag in
the observed repository state.

The next release loop is therefore:

1. obtain a qualifying independent review for the exact current head;
2. re-fetch the exact base and rebuild the synchronization candidate;
3. run the full repository, PostgreSQL, runtime, security, package, and
   provenance gates on that candidate;
4. merge only with current-head evidence and protected-branch rules satisfied;
5. publish an immutable versioned package and release notes;
6. then develop the next buyer-visible API gap from this file.

## Product boundary and observed capability

| Area | Current evidence | Buyer meaning |
| --- | --- | --- |
| Architecture decision authority | README, ADRs 0001–0004, normalized PostgreSQL migrations on the implementation line | Architecture and transformation decisions stay in this plane; employment and psychometric numerical truth stay in their owning products. |
| Independently operable runtime | `ea-core`, `/health`, and fail-closed `/ready` on the implementation line | An operator can check liveness first and dependency readiness second. |
| Technology-to-capability impact | Migration 0015, ADR 0016, and the technology target-state planner contract | A buyer can request a bitemporal impact decision with explicit evidence and next action once the exact implementation head is integrated and deployed. |
| Transformation lifecycle | Approval, schedule, start, complete, verification, monitoring, and replan routes in the latest stacked candidate | A buyer gets a governed decision trail; a planner or inferred fact cannot silently become an authoritative change. |
| Data/AI evidence loop | Receipt-bound cross-domain projections, assessment improvement, evidence closure, and reassessment status in the latest stacked candidate | Foreign data/AI systems remain authoritative while EA can expose accountable evidence gaps and next actions. |
| Relational integrity | 3NF migrations, tenant-bound foreign keys, forced RLS, temporal guards, outbox acceptance, and upgrade rehearsal on the implementation line | A buyer receives auditable history and tenant isolation evidence rather than a demo-only graph. |
| Presentation layer | `docs/STORYBOOK_INVENTORY.md` on the implementation line says no visual UI is shipped | This is intentionally headless. Add Figma/Storybook only when a presentation module and repeated web objects are approved. |

## Delivery truth classes

| Class | Evidence allowed | What it cannot prove |
| --- | --- | --- |
| `protected_baseline` | `develop` branch and its exact commit | It cannot prove that `main` or an open PR is integrated. |
| `implementation_candidate` | An exact PR head, diff, local tests, and current Checks | It cannot prove merge, release, deployment, or buyer availability. |
| `integrated` | Protected target-branch SHA after merge, fresh target-branch Checks, and ruleset evidence | It cannot prove a package is published or a runtime is deployed. |
| `released` | Immutable tag/release, package checksums/SBOM/provenance, and install smoke test | It cannot prove a customer deployment is healthy. |
| `live` | Authenticated runtime/browser/API evidence at the deployed environment | It cannot retroactively validate an older commit. |

## Current pull requests

The following inventory was collected from the repository’s open PR list. The
branch and PR names are public delivery identifiers; no personal or production
data is copied into this document. Checks are exact-head evidence and must be
recollected after any push or base change.

| PR | Scope | Base → head | Observed state | Customer-safe next action |
| ---: | --- | --- | --- | --- |
| [31](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/31) | Expose data-management reassessment status | `data-management-recheck-v1` → `data-management-recheck-status-v1` | Draft; newest workflow runs queued | Wait for terminal Checks, inspect review, then repair and revalidate the exact head. |
| [30](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/30) | Request data-management assessment recheck | `data-management-evidence-closure-v1` → `data-management-recheck-v1` | Draft; newest workflow runs queued | Validate the causal evidence boundary and terminal Checks before advancing the stack. |
| [29](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/29) | Accept data-management evidence and complete milestone | `data-management-improvement-v1` → `data-management-evidence-closure-v1` | Draft; last visible repository gates green | Re-fetch the exact head and obtain review before treating the slice as merge-ready. |
| [27](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/27) | Turn data-management gaps into improvement work | `target-state-replan-v1` → `data-management-improvement-v1` | Draft; visible repository gates green | Review the proposed remediation authority and preserve foreign-system ownership. |
| [26](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/26) | Make target-state replanning executable | `target-state-monitoring-v1` → `target-state-replan-v1` | Draft; visible repository gates green | Verify terminal `gap_detected` semantics and exact replay behavior. |
| [24](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/24) | Expose target-state monitoring freshness | `target-state-verification-v1` → `target-state-monitoring-v1` | Draft; visible repository gates green | Verify explicit valid/system cutoffs and stale-evidence next actions. |
| [23](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/23) | Record target-state verification | `target-state-complete-v1` → `target-state-verification-v1` | Draft; visible repository gates green | Confirm verification remains separate from completion and binds evidence. |
| [22](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/22) | Complete started target-state transformation | `target-state-start-v1` → `target-state-complete-v1` | Draft; visible repository gates green | Verify only an authoritative started transformation can complete. |
| [21](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/21) | Run repository acceptance on protected `develop` pushes | `main` → `fix/develop-push-acceptance` | Ready; exact current head Checks green; no qualifying independent current-head approval | Obtain a formal same-head approval, then re-fetch and re-check before merge. |
| [19](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/19) | Start scheduled target-state transformation | `target-state-schedule-v1` → `target-state-start-v1` | Draft; visible repository gates green | Review the schedule-to-start authority boundary before advancing. |
| [18](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/18) | Buyer README and architecture decision records | `develop` → `cursor/ea-core-customer-docs-609e` | Draft; documentation base is stale relative to the implementation line | Add this baseline, then adapt the docs to the exact integrated target head. |
| [17](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/17) | Schedule approved target-state transformation | `target-state-approval-v1` → `target-state-schedule-v1` | Draft; visible repository gates green | Review milestone binding and exact replay semantics. |
| [16](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/16) | Govern target-state approval command | `target-state-planner-api-v1` → `target-state-approval-v1` | Draft; visible repository gates green | Require operation-specific Keyverse authority and immutable evidence. |
| [15](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/15) | Expose authenticated target-state planner query | `target-state-planner-v1` → `target-state-planner-api-v1` | Draft; visible repository gates green | Verify issuer, audience, tenant, role, bitemporal cutoff, and no direct-table access. |
| [14](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/14) | Synchronize `main` into protected `develop` | `develop` ← `main` | Draft; blocked by review and base-sensitive integration evidence | Rebuild after prerequisite merges; do not transfer predecessor checks or reviews. |
| [12](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/12) | Joined technology target-state planner projection | `cross-domain-impact-projection-v1` → `target-state-planner-v1` | Draft; visible repository gates green | Preserve receipt-bound foreign evidence and deterministic next actions. |
| [11](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/11) | Cross-domain technology impact evidence | `main` → `cross-domain-impact-projection-v1` | Draft; visible repository gates green | Obtain review, then re-check exact base after integration changes. |

## Open issues and control-plane work

| Issue | Evidence-backed action |
| ---: | --- |
| [25](https://github.com/ContextualWisdomLab/enterprise-architecture-core/issues/25) | Convert data-management assessment gaps into evidence-backed improvement initiatives. Keep it linked to the implementation stack and close only after the acceptance evidence exists. |
| [20](https://github.com/ContextualWisdomLab/enterprise-architecture-core/issues/20) | Run repository acceptance on protected `develop` pushes. Verify the three workflow trigger boundaries after integration. |

The hourly organization PR loop belongs to the central `.github` control plane;
this repository’s product workflows remain responsible for repository,
runtime, and supply-chain evidence. A scheduled run is an invocation signal,
not a merge authorization. The loop must preserve the sequence
`review → repair → Checks → current-head gate → protected merge → next work`.

## Prioritized buyer gaps

| Priority | Gap | Current evidence | Buyer impact | Smallest next slice | Verified when |
| --- | --- | --- | --- | --- | --- |
| P0 | Protected integration truth is behind the implementation candidate | `develop` is the initialization baseline; `main` and stacked PRs contain the runtime and contracts; PRs #14 and #18 explicitly record stale-base risk | A buyer cannot tell which decision surface can be installed today. | Complete the exact-head review/Checks/merge loop for the stack root, then rebuild dependent PRs from the resulting protected SHA. | Protected target SHA contains the intended runtime/contracts, all required workflows are terminal green, and the target branch ruleset/review evidence is current. |
| P0 | No immutable customer release is observed | GitHub release/tag inventory is empty in this snapshot; package/SBOM workflows exist only as candidate evidence | A buyer cannot pin, install, verify, or roll back a product version. | Publish the first versioned package after protected integration and update `CHANGELOG.md` with the exact acceptance evidence. | Release tag, package checksums/SBOM/provenance, install smoke test, and rollback instructions all point to the same commit. |
| P0 | Shared Context Graph contract is release-gated rather than live-proven | `/ready` intentionally fails closed when the exact `cwl-context-contracts` distribution is unavailable; cross-domain acceptance remains conditional | Cross-product impact decisions cannot be promoted to production interoperability without a trusted contract artifact. | Publish or consume the exact immutable contract release through the approved connector boundary; keep unknown/mutable branches rejected. | Live `/ready` is 200 with the exact contract version, and cross-domain replay/tenant/authority acceptance passes against the released artifact. |
| P1 | Portfolio fit/scoring is normalized but not a buyer API | Crosswalk says the SQL assessment model exists while the scoring workflow/API remains unpublished | A portfolio owner still needs SQL or an adjacent product to answer fit, criticality, cost, and risk questions. | Define one authenticated, read-only assessment query contract with explicit tenant, valid-time, recorded-time, evidence, and next-action fields before adding UI. | OpenAPI, purpose-bound Keyverse reader, PostgreSQL acceptance, negative authorization tests, and a real runtime response are all current-head verified. |
| P1 | External lifecycle and data/AI adapters remain contract catalog entries | Connector catalog and receipt guards exist; vendor lifecycle and owner-produced production adapters are explicitly future work | Buyers see a safe integration boundary but still assemble feeds manually. | Add one highest-leverage REST/event adapter with canonical URI, receipt digest, replay, tenant, truth-origin, and failure-retry evidence. | The owning external system, released connector contract, real inbound receipt, replay test, and failure recovery are observed together. |
| P1 | Decision results are headless and lack an accessible buyer presentation surface | Storybook inventory explicitly records no visual UI | A non-technical buyer cannot yet explore capability maps, scenario comparison, or transformation timelines without a consuming product. | First approve a presentation-module boundary and repeated object inventory; then create Figma file/ADR linkage and Storybook tokens/components. | Browser E2E proves keyboard, screen-reader-equivalent text, exact-value alternatives, i18n consistency, and action edge cases against live API data. |
| P1 | CSAP/SOC 2 readiness is described but not an evidence pack | Security, threat, operability, and supply-chain documents exist; no certification or audit report is claimed by this repository | A regulated buyer cannot use the repository as an audit-ready control evidence pack. | Map implemented controls to NIST CSF 2.0 and AICPA Trust Services Criteria, then add owner, evidence location, cadence, and exception state. | Every claimed control has current executable or operational evidence; missing evidence remains explicitly `planned`, not `compliant`. |

## Deliberate non-gaps

- Do not move Orgmetra employment truth or fast-mlsirm psychometric kernels into
  this repository. Their canonical references and composition contracts are the
  product boundary.
- Do not add a graph database, LLM inference path, Rust/GPU numerical layer, or
  Figma/Storybook dependency to this headless foundation without a buyer
  outcome, owner, contract, and measured acceptance requirement.
- Do not mask accountable identifiers in a way that destroys audit utility.
  Keep raw personal attributes in the identity authority and expose only the
  minimum purpose-bound accountability reference here.
- Do not call an open PR, green check, mutable branch, or local Compose run a
  release. Use the delivery truth classes above.

## Doctoring and standards traceability

The current bibliography is maintained in [docs/REFERENCES.md](REFERENCES.md).
The baseline uses the following current or governing sources:

- ISO/IEC/IEEE 42010:2022 for architecture-description structure and the
  boundary between an architecture and its description.
- The Open Group TOGAF Standard, 10th Edition (C220) and ArchiMate 4 (C260)
  for target-state, capability, transformation, and viewpoint language.
- OpenAPI Specification 3.2.0 and CloudEvents 1.0.2 for machine-readable
  service and event interoperability.
- NIST CSF 2.0 and the AICPA Trust Services Criteria for security, supply
  chain, availability, processing integrity, confidentiality, and privacy
  evidence mapping.

All references in implementation ADRs and this baseline use APA 7th form. A
standard is not a conformance claim: the corresponding row must point to
current executable, runtime, or audit evidence.

