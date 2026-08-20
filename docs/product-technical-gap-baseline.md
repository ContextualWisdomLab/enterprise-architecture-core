# Product and technical gap baseline

**Snapshot:** 2026-08-20T22:53:58Z, GitHub inspection and repository inspection<br>
**Repository:** `ContextualWisdomLab/enterprise-architecture-core`<br>
**Decision record:** [ADR 0005](adr/0005-product-technical-gap-baseline.md)

This is an evidence snapshot, not a claim that every open branch is shipped.
Refresh it after a merge, base-branch change, release, failed check, or
material runtime change. The customer action in each row is the acceptance
test for the next loop.

**Live refresh:** `2026-08-20T22:53:58Z` — PR #18 was inspected at exact head
`d65bb9e78623f62139f6ef2a340eade703aeed4f`, based on protected
`develop@1c0fa8b15ceb9e72186274aeb255d6777eb84ef4`; its hosted checks are
queued after an exact-head dispatch and no formal approval is observed.
The synchronized stack is current at
PR #31 `172f439736753a14cdb6569b954adb1cf905bc44`, PR #32
`03b3d560ce29a9441119995134a028a69edab315`, PR #33
`d024aab7031d628be64a589a846b15a6f883746f`, and PR #35
`6eab7bae3e2e7424ac33fbd74a3953e2a3949596`; their exact bases are recorded
below, hosted required Checks were re-queued after the current-head pushes, and
no formal same-head approval is observed. PR #34 is an independent `main` candidate at exact head
`b6160bdf1ac9c7f9511c9261b7032f853d591f15` with hosted Checks queued. Local
PR34 evidence passes 121 tests, 100% statement-and-branch coverage (436
statements/162 branches), Ruff, and repository validation; current PR35 evidence
passes 698 tests, 100% statement-and-branch coverage (3250 statements/900
branches), Ruff, repository validation (`48 tables, 399 columns, 22 indexes,
416 constraints, 14 OpenAPI operations, 12 AsyncAPI operations, 7 connectors,
25 ADRs`), clean PostgreSQL 18 SQL acceptance through migration 0050, and
runtime privilege acceptance. These local results do
not prove hosted Checks, merge, release, or deployment.

## Executive decision

The product has a credible headless decision-plane foundation and a growing
authenticated transformation decision surface. The buyer-facing blocker is
delivery truth: the protected default branch is still the initialization
baseline while runtime and later decision capabilities are represented by
`implementation_candidate` branches and stacked pull requests. Deployable and
buyer-available truth requires the corresponding exact package, release, and
live evidence. There is no GitHub release or version tag in the observed
repository state.

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
| Technology-to-capability impact | Migration 0015, ADR 0016, and the technology target-state planner contract on an `implementation_candidate` head | A buyer can request a bitemporal impact decision with explicit evidence and next action once the exact implementation head is integrated and deployed. |
| Transformation lifecycle | Approval, schedule, start, complete, verification, monitoring, and replan routes in the latest `implementation_candidate` stack; not buyer-available until integrated and released | A buyer gets a governed decision trail; a planner or inferred fact cannot silently become an authoritative change. |
| Data/AI evidence loop | Receipt-bound cross-domain projections, assessment improvement, evidence closure, and reassessment status in the latest `implementation_candidate` stack; not buyer-available until integrated and released | Foreign data/AI systems remain authoritative while EA can expose accountable evidence gaps and next actions. |
| Relational integrity | 3NF migrations, tenant-bound foreign keys, forced RLS, temporal guards, outbox acceptance, and upgrade rehearsal on the implementation line | A buyer receives auditable history and tenant isolation evidence rather than a demo-only graph. |
| Hot-write capacity preparation | Migration 0050 and ADR 0025 on PR #35 exact head `6eab7bae3e2e7424ac33fbd74a3953e2a3949596` define deterministic tenant-derived 16-bucket routing, storage headroom, and hot-write indexes; clean PostgreSQL 18 SQL and runtime privilege acceptance pass; physical partition deployment is not claimed | A buyer gets an explicit capacity-migration boundary, while production skew, queue lag, and write amplification still require measurement. |
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
| [35](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/35) | Prepare append-only write boundaries for hot partitioning | `portfolio-assessment-summary` at current base `d024aab7031d628be64a589a846b15a6f883746f` → `hot-write-capacity` | Ready; exact head `6eab7bae3e2e7424ac33fbd74a3953e2a3949596`; PR33 current head was propagated and the merge conflict was resolved without dropping either chain; current evidence is 698 tests, 100% statement-and-branch coverage, Ruff, repository validation, clean PostgreSQL 18 SQL/runtime acceptance; hosted required Checks were re-queued; no formal approval | Wait for terminal Checks and an independent same-head review; merge only after PR #33 and its ancestors are current and protected. |
| [34](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/34) | Repair protected-main SPDX attestation compatibility | `main` at current base `ca6889497728e1a3f09d68790a9096576e13a3ff` → `codex/supply-chain-sbom-attestation` | Ready; exact head `b6160bdf1ac9c7f9511c9261b7032f853d591f15`; local current-head evidence passes 121 tests, 100% statement-and-branch coverage (436 statements/162 branches), Ruff, and repository validation; hosted Checks are queued; no formal approval | Wait for terminal hosted Checks and an independent same-head review; merge only after the exact-head protected gate passes. |
| [33](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/33) | Publish deterministic portfolio assessment summary | `portfolio-assessment-api` at current base `03b3d560ce29a9441119995134a028a69edab315` → `portfolio-assessment-summary` | Ready; exact head `d024aab7031d628be64a589a846b15a6f883746f`; portfolio contract count was refreshed to 14 operations; current PR35 aggregate evidence covers the synchronized chain; hosted Checks were re-queued; no formal approval | Wait for terminal Checks and obtain an independent same-head review; merge only after the synchronized parent and descendant gates are current. |
| [32](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/32) | Expose portfolio assessment read port | `data-management-recheck-status-v1` at current base `172f439736753a14cdb6569b954adb1cf905bc44` → `portfolio-assessment-api` | Ready; exact head `03b3d560ce29a9441119995134a028a69edab315`; 674 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; hosted Checks were re-queued; no formal approval | Wait for terminal Checks and obtain an independent same-head review; repair and revalidate before merge. |
| [31](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/31) | Expose data-management reassessment status | `data-management-recheck-v1` at current base `073b6420f9c74033c166580a1f01c13d20c8ee30` → `data-management-recheck-status-v1` | Ready; exact head `172f439736753a14cdb6569b954adb1cf905bc44`; synchronized parent of the portfolio API; hosted Checks were re-queued; no formal approval | Wait for terminal Checks, inspect the independent review, then merge only with current-head evidence. |
| [30](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/30) | Request data-management assessment recheck | `data-management-evidence-closure-v1` at current base `25a83ab1b61892b5376284b9e396ccf134a55aee` → `data-management-recheck-v1` | Ready; exact head `073b6420f9c74033c166580a1f01c13d20c8ee30`; 614 tests, 100% coverage, repository validation, clean PostgreSQL 18 acceptance, and no unresolved current CodeRabbit finding; hosted Checks were re-queued; no formal approval | Validate the causal evidence boundary and terminal Checks before advancing the stack. |
| [29](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/29) | Accept data-management evidence and complete milestone | `data-management-improvement-v1` → `data-management-evidence-closure-v1` | Ready; last visible repository gates green; exact-head OpenCode review dispatched | Re-fetch the exact head and obtain review before treating the slice as merge-ready. |
| [27](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/27) | Turn data-management gaps into improvement work | `target-state-replan-v1` → `data-management-improvement-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Review the proposed remediation authority and preserve foreign-system ownership. |
| [26](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/26) | Make target-state replanning executable | `target-state-monitoring-v1` → `target-state-replan-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Verify terminal `gap_detected` semantics and exact replay behavior. |
| [24](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/24) | Expose target-state monitoring freshness | `target-state-verification-v1` → `target-state-monitoring-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Verify explicit valid/system cutoffs and stale-evidence next actions. |
| [23](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/23) | Record target-state verification | `target-state-complete-v1` → `target-state-verification-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Confirm verification remains separate from completion and binds evidence. |
| [22](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/22) | Complete started target-state transformation | `target-state-start-v1` → `target-state-complete-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Verify only an authoritative started transformation can complete. |
| [21](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/21) | Run repository acceptance on protected `develop` pushes | `main` → `fix/develop-push-acceptance` | Ready; exact current head `4ada32a811c2f5ba7ac2138c0826229c5d62e78b`; repository Checks terminal green; exact-head OpenCode dispatch was accepted; no qualifying independent current-head approval | Obtain a formal same-head approval, then re-fetch and re-check before merge. |
| [19](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/19) | Start scheduled target-state transformation | `target-state-schedule-v1` → `target-state-start-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Review the schedule-to-start authority boundary before advancing. |
| [18](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/18) | Buyer README and architecture decision records | `develop` at current base `1c0fa8b15ceb9e72186274aeb255d6777eb84ef4` → `cursor/ea-core-customer-docs-609e` | Ready; exact head `d65bb9e78623f62139f6ef2a340eade703aeed4f`; exact-head OpenCode dispatch accepted and its review job is pending; no formal approval | Obtain an independent same-head review, diagnose only current-head failures, and re-fetch all terminal Checks before merge. |
| [17](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/17) | Schedule approved target-state transformation | `target-state-approval-v1` → `target-state-schedule-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Review milestone binding and exact replay semantics. |
| [16](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/16) | Govern target-state approval command | `target-state-planner-api-v1` → `target-state-approval-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Require operation-specific Keyverse authority and immutable evidence. |
| [15](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/15) | Expose authenticated target-state planner query | `target-state-planner-v1` → `target-state-planner-api-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Verify issuer, audience, tenant, role, bitemporal cutoff, and no direct-table access. |
| [14](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/14) | Synchronize `main` into protected `develop` | `develop` ← `main` | Ready; exact head `ca6889497728e1a3f09d68790a9096576e13a3ff`; latest required Checks pass; older attestation/runtime failures are stale; exact-head OpenCode review dispatched | Rebuild after prerequisite merges; do not transfer predecessor checks or reviews. |
| [12](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/12) | Joined technology target-state planner projection | `cross-domain-impact-projection-v1` → `target-state-planner-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Preserve receipt-bound foreign evidence and deterministic next actions. |
| [11](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/11) | Cross-domain technology impact evidence | `main` → `cross-domain-impact-projection-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Obtain review, then re-check exact base after integration changes. |

### Current-head evidence packet

The original exact-head packet was collected at `2026-08-20T13:06:28Z`; the
current synchronized stack and PR18/PR35 rows were refreshed at
`2026-08-20T22:53:58Z` from GitHub inspection and local acceptance runs. Every open PR is classified as
an `implementation_candidate`; that class does not imply merge, release,
deployment, or buyer availability. The full SHA is the identity to re-fetch
after any push or base-branch change.

| PR | Full head SHA | Collected | Delivery truth | Current evidence boundary |
| ---: | --- | --- | --- | --- |
| 35 | `6eab7bae3e2e7424ac33fbd74a3953e2a3949596` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current head includes PR33 propagation and hot-write capacity; 698 tests, 100% statement-and-branch coverage (3250 statements/900 branches), Ruff, repository validation, clean PostgreSQL 18 migrations 0001–0050, every SQL acceptance file, and runtime privilege acceptance; hosted Checks re-queued; no formal approval. |
| 34 | `b6160bdf1ac9c7f9511c9261b7032f853d591f15` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current-head local evidence passes 121 tests, 100% statement-and-branch coverage (436 statements/162 branches), Ruff, and repository validation; workflow-specific hosted SBOM/attestation Checks are queued; no formal approval, merge, release, or live deployment is claimed. |
| 33 | `d024aab7031d628be64a589a846b15a6f883746f` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Portfolio summary contract count refreshed to 14 operations; current PR35 aggregate local evidence covers this exact chain; hosted Checks re-queued; no formal approval. |
| 32 | `03b3d560ce29a9441119995134a028a69edab315` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Portfolio API and isolated reassessment fixtures; 674 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; hosted Checks re-queued; no formal approval. |
| 31 | `172f439736753a14cdb6569b954adb1cf905bc44` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Synchronized status parent of PR32; current PR35 aggregate local evidence covers the status contract and PostgreSQL fixture; hosted Checks re-queued; no formal approval. |
| 30 | `073b6420f9c74033c166580a1f01c13d20c8ee30` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current ancestor with 614-test/100%-coverage, repository, clean PostgreSQL 18 acceptance, and terminal local evidence; no formal approval or protected integration is observed. |
| 29 | `25a83ab1b61892b5376284b9e396ccf134a55aee` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current data-management evidence-closure ancestor; 579 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 27 | `8815b281f1ec5804bc1d2e9a3d210fbc1187e6f1` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current improvement ancestor; replay-before-liveness and test-isolation fixes pass 542 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance; no protected integration or formal approval. |
| 26 | `3cd77d37ef9523e28215e646e234c11cd7ae813f` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state replan ancestor; 531 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 24 | `d5b3e412beae62c49aea9f969eff374c83935e46` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state monitoring ancestor; 483 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 23 | `ab3f45cde91f128571892fd6b56d367771fd896f` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state verification ancestor; 441 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 22 | `a47a49c7baa415733a0d455f898de397b54999cd` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state completion ancestor; 392 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 21 | `4ada32a811c2f5ba7ac2138c0826229c5d62e78b` | `2026-08-20T14:22:40Z` | `implementation_candidate` | Repository Checks terminal green; exact-head OpenCode dispatch was accepted; no qualifying independent current-head approval observed. |
| 19 | `03a5898cc7a73eb55ed87198c8392965ff9ee793` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state start ancestor; 341 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 18 | `d65bb9e78623f62139f6ef2a340eade703aeed4f` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Documentation snapshot source head; exact-head OpenCode dispatch accepted and its review job is pending; no formal current-head approval observed. |
| 17 | `272571a480bda9ed75267af1617fac5a6f9018a0` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state schedule ancestor; 287 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 16 | `cb342b116a55b14d8caf4600141295ae35f7309d` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state approval ancestor; 231 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance pass; no protected integration or formal approval. |
| 15 | `cda7aa69c853d3ea2292c14a47d51eaea4b0fe0d` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state planner API ancestor; local stack propagation completed and exact-head review dispatch is required; no protected integration or formal approval. |
| 14 | `ca6889497728e1a3f09d68790a9096576e13a3ff` | `2026-08-20T13:06:28Z` | `implementation_candidate` | Open draft integration candidate; no protected integration, immutable release, or live deployment evidence observed. |
| 12 | `3e070cd57f8aafdb5a87560b4e6089bdf2ebbd1c` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state planner ancestor; exact-head review dispatch and protected current-head checks remain required. |
| 11 | `1282d46af8f65a970a337d6496b15397c29ecd41` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current cross-domain impact ancestor; exact-head review dispatch and protected current-head checks remain required. |

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
| P0 | Protected integration truth is behind the implementation candidate | At `2026-08-20T13:06:28Z`, protected `develop@1c0fa8b15ceb9e72186274aeb255d6777eb84ef4` is the initialization baseline and `main@ca6889497728e1a3f09d68790a9096576e13a3ff` is an unmerged source branch; PRs #14 and #18 explicitly record stale-base risk | A buyer cannot tell which decision surface can be installed today. | Complete the exact-head review/Checks/merge loop for the stack root, then rebuild dependent PRs from the resulting protected SHA. | Protected target SHA contains the intended runtime/contracts, all required workflows are terminal green, and the target branch ruleset/review evidence is current. |
| P0 | No immutable customer release is observed | At `2026-08-20T13:06:28Z`, GitHub release/tag inventory is empty; package/SBOM workflows exist only as candidate evidence | A buyer cannot pin, install, verify, or roll back a product version. | Publish the first versioned package after protected integration and update `CHANGELOG.md` with the exact acceptance evidence. | Release tag, package checksums/SBOM/provenance, install smoke test, and rollback instructions all point to the same commit. |
| P0 | Shared Context Graph contract is release-gated rather than live-proven | At `2026-08-20T13:06:28Z`, `/ready` intentionally fails closed when the exact `cwl-context-contracts` distribution is unavailable; no immutable contract version or live positive readiness evidence is observed | Cross-product impact decisions cannot be promoted to production interoperability without a trusted contract artifact. | Publish or consume the exact immutable contract release through the approved connector boundary; keep unknown/mutable branches rejected. | Live `/ready` is 200 with the exact contract version, and cross-domain replay/tenant/authority acceptance passes against the released artifact. |
| P1 | Portfolio fit/scoring is normalized but not a buyer API | PR [32](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/32) at exact head `03b3d560ce29a9441119995134a028a69edab315` adds the authenticated single-object assessment read port; synchronized PR [33](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/33) at exact head `d024aab7031d628be64a589a846b15a6f883746f` adds the deterministic summary candidate | A portfolio owner still needs an aggregate fit, criticality, cost, and risk answer on the protected branch. | Complete the current-head review and Checks loop for #32, then repeat it for the synchronized summary while preserving tenant, valid-time, recorded-time, truth status, evidence, and next-action fields. | The integrated summary has an OpenAPI contract, purpose-bound reader, deterministic PostgreSQL acceptance, negative authorization tests, and a current-head runtime response. |
| P1 | Append-only database write hot spots lack buyer-observed capacity evidence | PR [35](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/35) at exact head `6eab7bae3e2e7424ac33fbd74a3953e2a3949596` adds migration 0050, ADR 0025, deterministic 16-bucket tenant routing, fillfactor headroom, hot-write indexes, and clean/upgrade PostgreSQL acceptance; physical partitions and production skew measurements remain absent | A buyer cannot yet distinguish a measured high-write operating envelope from a schema prepared for future scale. | Merge the reviewed stack, then measure tenant skew, queue lag, write amplification, and index behavior on representative authorized data before proposing a physical HASH/LIST cutover. | Protected integration and a repeatable PostgreSQL capacity report bind the same migration, measurements, RLS behavior, and rollback evidence; no production capacity claim is made before then. |
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

## Documentation and standards traceability

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
