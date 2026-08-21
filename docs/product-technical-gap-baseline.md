# Product and technical gap baseline

**Snapshot:** 2026-08-21T05:11:03Z, GitHub inspection, repository inspection, and local runtime probe<br>
**Repository:** `ContextualWisdomLab/enterprise-architecture-core`<br>
**Decision records:** [ADR 0005](adr/0005-product-technical-gap-baseline.md), [ADR 0006](adr/0006-security-control-evidence-boundary.md)

This is an evidence snapshot, not a claim that every open branch is shipped.
Refresh it after a merge, base-branch change, release, failed check, or
material runtime change. The customer action in each row is the acceptance
test for the next loop.

**Runtime refresh:** At exact PR36 head `ee9d5bcb38507b32c86486dce3480733ab72c4ce`,
the project-local virtualenv served `GET /health` with HTTP 200 and
`GET /ready` with HTTP 503 (`contract_ready=false`, `database_ready=false`).
This proves the local process probe and intentional fail-closed behavior only;
it is not protected integration, release, deployment, or production evidence.

**Verification refresh:** At the same exact PR36 head, the isolated local run
passed 703 Python tests with 100% statement-and-branch coverage (3,252
statements and 902 branches), Ruff, repository validation, and Semgrep with
zero findings. Clean PostgreSQL 18.6 runs applied 50 migrations and passed 63
SQL acceptance files across 48 tables; a separate `ea_runtime` acceptance run
passed the non-superuser and direct-table-access boundary. These are local
candidate-head results, not protected integration or release evidence.

**Live refresh:** `2026-08-21T05:11:03Z` — PR29 is current at
`3e9edee4a57e7adde60d96522f29d34f5c95559d`, after the Python support-boundary
Semgrep suppression and uv seven-day dependency cooldown repair; PR30 is
current at `6026fb4a186f59bc431c087f2ba94fee2bcfe314` and carries that repaired
parent. PR31→PR32→PR33→PR35→PR36 now form an exact synchronized stack at
`110142f0cc52c835095325426a6edc17a12d9366` →
`deef9f7e7b5b61f3f00c9392c8d5fbb75a27978a` →
`e157633e322098a78ddba8db8a283aeaf2de7482` →
`d8d0cc71b099c71d30fd40d7b7bd1adfefb227f0` →
`ee9d5bcb38507b32c86486dce3480733ab72c4ce`. The local candidate evidence is
recorded above; all current hosted required Checks are queued and no formal
same-head approval is observed. This PR18 refresh itself is source head
`8562545f6d8c4ebc62e47eab63f86c6b9763f19b` on protected
`develop@1c0fa8b15ceb9e72186274aeb255d6777eb84ef4`.

The current-head PostgreSQL fixture-order repair was also applied to PR #17
`75e2f55b1e24724f007448734abe30f521668ce7`, PR #19
`6764f5eabfb26c782e2067cf35bc084dca22f2a3`, PR #23
`88b0d083f1abcb639fab3d17b63166da4428ac78`, PR #24
`d19a5e70b9746eb0f4bcfdc27b87d445ac4ec7f8`, while PR #26 is current at
`a5cfad3419d35246a724da1909c95beb6f9ff3d1` with transaction-isolated planner
fixture writes. Each full local SQL acceptance
suite passed on PostgreSQL 18 with the CI application role; their hosted
Checks are queued and the PRs remain Draft. PR #33 is current at
`e157633e322098a78ddba8db8a283aeaf2de7482`, with the same clean PostgreSQL
18 portfolio fixture assertion repair plus the current PR32 parent; its hosted
Checks are queued and it remains Draft. No formal same-head approval or
protected merge is observed.

PR #36 extends PR35 at exact head
`ee9d5bcb38507b32c86486dce3480733ab72c4ce` with the operator runbook and
failure-safe tenant-context restoration for the repeatable tenant-scoped
hot-write snapshot; the current propagated stack passes 703 Python tests with
100% statement-and-branch coverage, Ruff, repository validation, and all 63
SQL acceptance files on clean PostgreSQL 18.6 with 50 migrations and 48
tables; the docs-only shell continuation fix passes diff validation. PR #12
has exact head
`4f614fb96047fe1d6e844fec4998ac465b09ec06` after a RED regression reproduced
superseded-current projection leakage; the minimal predicate repair preserves
historical visibility, and all 22 SQL acceptance files pass on a clean
PostgreSQL 18.6 installation. The public Checks pages currently show PR32,
PR33, PR35, and PR36 with 19 queued and 7 skipped jobs each, and PR18 with
queued jobs; all
remain Draft with no formal same-head approval. PR22 has queued jobs after its
current-head fixture-isolation repair, plus
PR17, PR19, PR23, PR24, PR26, PR33, PR34, PR35, and PR36 with queued jobs.
PR #11's prior exact-head Strix run at `1282d46af8f65a970a337d6496b15397c29ecd41`
reported one `CRITICAL` hardcoded-credential finding in the changed workflow
surface and failed closed. Its current repair head is
`f57cf99d4597a610590746d6c316c4a27dc3999a`; the fixed literals were removed,
run-scoped credentials are generated or injected at runtime, and the
compose-runtime step exports generated credentials before starting Compose.
Focused tests, actionlint, repository validation, and the direct Compose
configuration check pass locally; new hosted Checks are pending.
PR14's prior failures on its unchanged `main` head remain historical:
`attest-protected-main` run `32036084953` rejected the old SPDX payload as
unsupported, while `installed-process-readiness` run `32036084876` failed
after three codeload HTTP 429 attempts for `astral-sh/setup-uv`. Attempt-2
reruns for both jobs are queued at `2026-08-21T05:56:13Z`; their completion is
not inferred. The attestation failure is addressed by PR34 at current head
`ab8283ed0c51ffea5efebd4803c7a10e2b744f62`.
PR #29's repaired exact head `3e9edee4a57e7adde60d96522f29d34f5c95559d` and
PR #30's propagated exact head `6026fb4a186f59bc431c087f2ba94fee2bcfe314`
both pass the local full Semgrep scan with zero findings; the previous
multi-language failures belonged to superseded heads and are not converted
into current-head success until hosted Checks finish.

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
| Hot-write capacity preparation | Migration 0050 and ADR 0025 on PR #35 exact head `d8d0cc71b099c71d30fd40d7b7bd1adfefb227f0` define deterministic tenant-derived 16-bucket routing, storage headroom, and hot-write indexes; PR #36 exact head `ee9d5bcb38507b32c86486dce3480733ab72c4ce` adds a read-only tenant-scoped capacity snapshot, failure-safe context restoration, and operator runbook for row volume, queue lag, bucket, relation/index size, and cumulative tuple/WAL comparison; the current stack passes 63 clean PostgreSQL 18.6 SQL acceptance files; physical partition deployment is not claimed | A buyer gets a repeatable measurement baseline, while production capacity and partition cutover still require authorized representative-data evidence. |
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
| [36](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/36) | Add repeatable hot-write capacity snapshot | `hot-write-capacity` at current base `d8d0cc71b099c71d30fd40d7b7bd1adfefb227f0` → `codex/hot-write-capacity-report` | Draft; exact head `ee9d5bcb38507b32c86486dce3480733ab72c4ce`; current stack passes 703 Python tests with 100% statement-and-branch coverage, Ruff, repository validation, zero local Semgrep findings, and 63 clean PostgreSQL 18.6 SQL acceptance files; hosted Checks 19 queued and 7 skipped; no formal approval | Obtain an independent same-head review and terminal Checks; merge only after the exact current stack is valid. |
| [35](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/35) | Prepare append-only write boundaries for hot partitioning | `portfolio-assessment-summary` at current base `e157633e322098a78ddba8db8a283aeaf2de7482` → `hot-write-capacity` | Draft; exact head `d8d0cc71b099c71d30fd40d7b7bd1adfefb227f0`; current parent propagation retains the scoped inferred-dimension assertion and the stack’s 703-test/100%-coverage, Ruff, repository, and PostgreSQL evidence; hosted Checks 19 queued and 7 skipped; no formal approval | Wait for terminal Checks and an independent same-head review; merge only after the exact current stack is valid. |
| [34](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/34) | Repair protected-main SPDX attestation compatibility | `main` at current base `ca6889497728e1a3f09d68790a9096576e13a3ff` → `codex/supply-chain-sbom-attestation` | Draft; exact head `ab8283ed0c51ffea5efebd4803c7a10e2b744f62`; verifier binds the signed SPDX predicate to the downloaded SBOM snapshot; 134 tests, Ruff, and `bash -n` pass locally; hosted Checks are queued; no formal approval | Keep the external Draft state intact, then obtain terminal hosted Checks and an independent same-head review before merge. |
| [33](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/33) | Publish deterministic portfolio assessment summary | `portfolio-assessment-api` at current base `deef9f7e7b5b61f3f00c9392c8d5fbb75a27978a` → `portfolio-assessment-summary` | Draft; exact head `e157633e322098a78ddba8db8a283aeaf2de7482`; portfolio contract count remains 14 operations, the inferred fixture assertion is dimension-scoped, and the full local PostgreSQL 18 suite plus current parent tests pass; hosted Checks 19 queued and 7 skipped; no formal approval | Keep the external Draft state intact, then obtain terminal Checks and an independent same-head review. |
| [32](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/32) | Expose portfolio assessment read port | `data-management-recheck-status-v1` at base `110142f0cc52c835095325426a6edc17a12d9366` → `portfolio-assessment-api` | Draft; exact head `deef9f7e7b5b61f3f00c9392c8d5fbb75a27978a`; current parent propagation preserves the PR31 status fixes, dimension-scoped portfolio acceptance, 682 tests with 100% coverage, Ruff, repository validation, and 61 SQL acceptance files; hosted Checks 19 queued and 7 skipped; no formal approval | Keep the external Draft state intact, then obtain terminal Checks and an independent same-head review. |
| [31](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/31) | Expose data-management reassessment status | `data-management-recheck-v1` at current base `6026fb4a186f59bc431c087f2ba94fee2bcfe314` → `data-management-recheck-status-v1` | Draft; exact head `110142f0cc52c835095325426a6edc17a12d9366`; 649 tests, 100% statement-and-branch coverage, Ruff, and full PostgreSQL 18 acceptance pass after the fixture/validator repair; hosted Checks are 19 queued and 7 skipped with no current failure; no formal approval | Keep the external Draft state intact, then obtain terminal Checks and an independent same-head review before propagating this repaired parent. |
| [30](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/30) | Request data-management assessment recheck | `data-management-evidence-closure-v1` at current base `3e9edee4a57e7adde60d96522f29d34f5c95559d` → `data-management-recheck-v1` | Draft; exact head `6026fb4a186f59bc431c087f2ba94fee2bcfe314`; 614 tests, 100% coverage, repository validation, clean PostgreSQL 18 acceptance, and local full Semgrep zero findings; hosted Checks are queued after parent propagation; no formal approval | Keep the external Draft state intact; obtain terminal hosted Semgrep and the remaining required Checks before treating the stack as merge-ready. |
| [29](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/29) | Accept data-management evidence and complete milestone | `data-management-improvement-v1` → `data-management-evidence-closure-v1` | Ready; exact head `3e9edee4a57e7adde60d96522f29d34f5c95559d`; local full Semgrep is zero findings after the Python support-boundary and uv cooldown repairs; hosted Checks are queued and no formal approval is observed. | Obtain terminal hosted Checks and an independent same-head review before advancing the milestone. |
| [27](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/27) | Turn data-management gaps into improvement work | `target-state-replan-v1` → `data-management-improvement-v1` | Ready; exact head `8815b281f1ec5804bc1d2e9a3d210fbc1187e6f1`; 25 repository Checks are green, with exact-head OpenCode and Devin review pending; no formal approval | Obtain independent same-head review and terminal current-head gates while preserving foreign-system ownership. |
| [26](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/26) | Make target-state replanning executable | `target-state-monitoring-v1` → `target-state-replan-v1` | Draft; exact head `a5cfad3419d35246a724da1909c95beb6f9ff3d1`; 531 Python tests, 100% statement-and-branch coverage, Ruff, repository validation, and the exact PostgreSQL 18.4 acceptance loop pass after transaction-isolating the planner fixture; current Checks are queued; no formal approval | Keep the external Draft state intact, then verify terminal `gap_detected` semantics and exact replay behavior. |
| [24](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/24) | Expose target-state monitoring freshness | `target-state-verification-v1` → `target-state-monitoring-v1` | Draft; exact head `d19a5e70b9746eb0f4bcfdc27b87d445ac4ec7f8`; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; current Checks have no reported failure and remain queued | Keep the external Draft state intact, then verify explicit valid/system cutoffs and stale-evidence next actions. |
| [23](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/23) | Record target-state verification | `target-state-complete-v1` → `target-state-verification-v1` | Draft; exact head `88b0d083f1abcb639fab3d17b63166da4428ac78`; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; current Checks have no reported failure and remain queued | Keep the external Draft state intact, then confirm verification remains separate from completion and binds evidence. |
| [22](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/22) | Complete started target-state transformation | `target-state-start-v1` → `target-state-complete-v1` | Ready; exact head `a85e4c6466545369c675f4055de99bd836bc7967`; planner fixture supersession is transaction-isolated, and all 29 local PostgreSQL 18.4 SQL acceptance files pass; hosted Checks re-queued; no formal approval | Obtain an independent same-head review and terminal Checks; verify only an authoritative started transformation can complete. |
| [21](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/21) | Run repository acceptance on protected `develop` pushes | `main` → `fix/develop-push-acceptance` | Ready; exact current head `4ada32a811c2f5ba7ac2138c0826229c5d62e78b`; repository Checks terminal green; exact-head OpenCode dispatch was accepted; no qualifying independent current-head approval | Obtain a formal same-head approval, then re-fetch and re-check before merge. |
| [19](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/19) | Start scheduled target-state transformation | `target-state-schedule-v1` → `target-state-start-v1` | Draft; exact head `6764f5eabfb26c782e2067cf35bc084dca22f2a3`; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; current Checks have no reported failure and remain queued | Keep the external Draft state intact, then review the schedule-to-start authority boundary before advancing. |
| [18](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/18) | Buyer README and architecture decision records | `develop` at current base `1c0fa8b15ceb9e72186274aeb255d6777eb84ef4` → `cursor/ea-core-customer-docs-609e` | Draft; documentation refresh at exact source head `8562545f6d8c4ebc62e47eab63f86c6b9763f19b`; evidence baseline includes the current PR12, PR16, scheduler, synchronized PR29→30→31→32→33→35→36 stack, and final local runtime/coverage/PostgreSQL evidence; hosted Checks 10 queued; no formal approval | Keep the external Draft state intact, then obtain an independent same-head review and re-fetch all terminal Checks before merge. |
| [17](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/17) | Schedule approved target-state transformation | `target-state-approval-v1` → `target-state-schedule-v1` | Draft; exact head `75e2f55b1e24724f007448734abe30f521668ce7`; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; current Checks have no reported failure and remain queued | Keep the external Draft state intact, then review milestone binding and exact replay semantics. |
| [16](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/16) | Govern target-state approval command | `target-state-planner-api-v1` → `target-state-approval-v1` | Ready; exact head `8f852ac54b3636d147c37b6c5b652bf7a16e1ee6`; fixture-isolation repair passes 231 Python tests with 100% statement-and-branch coverage, Ruff, repository validation, and all 25 real PostgreSQL 18.6 acceptance files; exact-head OpenCode dispatch accepted; hosted Checks queued; no formal approval | Obtain an independent same-head review and terminal Checks; merge only after the approval role boundary and immutable database acceptance remain green. |
| [15](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/15) | Expose authenticated target-state planner query | `target-state-planner-v1` → `target-state-planner-api-v1` | Ready; visible repository gates green; exact-head OpenCode review dispatched | Verify issuer, audience, tenant, role, bitemporal cutoff, and no direct-table access. |
| [14](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/14) | Synchronize `main` into protected `develop` | `develop` ← `main` | Draft; exact head `ca6889497728e1a3f09d68790a9096576e13a3ff`; `attest-protected-main` run `32036084953` rejected the old SPDX payload as unsupported, and `installed-process-readiness` run `32036084876` failed after three setup-uv codeload HTTP 429 attempts; no current-head approval | Wait for PR34's protected-main fix to integrate into `main`, then rebuild/recheck PR14; do not rerun unchanged external 429 evidence or transfer predecessor checks. |
| [12](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/12) | Joined technology target-state planner projection | `cross-domain-impact-projection-v1` → `target-state-planner-v1` | Draft; exact head `4f614fb96047fe1d6e844fec4998ac465b09ec06`; a RED regression reproduced superseded-current projection leakage, the predicate repair preserves historical visibility, and all 22 SQL acceptance files pass on clean PostgreSQL 18.6; hosted Checks 19 queued and 7 skipped; no formal approval | Preserve receipt-bound foreign evidence and deterministic next actions; obtain an independent same-head review and terminal Checks before protected merge. |
| [11](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/11) | Cross-domain technology impact evidence | `main` → `cross-domain-impact-projection-v1` | Ready; exact repair head `f57cf99d4597a610590746d6c316c4a27dc3999a`; prior Strix run at `1282d46af8f65a970a337d6496b15397c29ecd41` found one CRITICAL hardcoded-credential finding; workflow credential repair passes local contract tests, actionlint, repository validation, direct Compose configuration, and real PostgreSQL runtime/RLS acceptance; current Checks are pending | Verify the new exact-head Strix result and obtain independent review before merge. |

### Current-head evidence packet

The original exact-head packet was collected at `2026-08-20T13:06:28Z`; the
current PR18 row and failed-check evidence were refreshed at
`2026-08-21T00:34:02Z` from GitHub inspection and local acceptance runs. Every open PR is classified as
an `implementation_candidate`; that class does not imply merge, release,
deployment, or buyer availability. The full SHA is the identity to re-fetch
after any push or base-branch change.

| PR | Full head SHA | Collected | Delivery truth | Current evidence boundary |
| ---: | --- | --- | --- | --- |
| 36 | `ee9d5bcb38507b32c86486dce3480733ab72c4ce` | `2026-08-21T04:39:00Z` | `implementation_candidate` | Tenant-scoped read-only hot-write snapshot plus operator runbook; the propagated stack passes 703 tests with 100% statement-and-branch coverage, Ruff, repository validation, zero local Semgrep findings, and 63 clean PostgreSQL 18.6 SQL acceptance files across 50 migrations and 48 tables; hosted Checks 19 queued and 7 skipped; no formal approval, merge, release, or production-capacity claim. |
| 35 | `d8d0cc71b099c71d30fd40d7b7bd1adfefb227f0` | `2026-08-21T04:39:00Z` | `implementation_candidate` | Current hot-write capacity head includes the synchronized portfolio summary parent; parent propagation retains the dimension-scoped assertion and 703-test/100%-coverage local evidence, with hosted Checks 19 queued and 7 skipped; no formal approval. |
| 34 | `ab8283ed0c51ffea5efebd4803c7a10e2b744f62` | `2026-08-21T05:11:03Z` | `implementation_candidate` | Current-head verifier binds the signed SPDX predicate to the downloaded SBOM snapshot; 134 tests, Ruff, and `bash -n` pass locally; hosted Checks are queued; no formal approval, merge, release, or live deployment is claimed. |
| 33 | `e157633e322098a78ddba8db8a283aeaf2de7482` | `2026-08-21T04:39:00Z` | `implementation_candidate` | Portfolio summary contract count remains 14 operations; the inferred assessment assertion is scoped to its dimension, the current PR32 parent is propagated, and the full local PostgreSQL 18 suite passes; hosted Checks 19 queued and 7 skipped; Draft; no formal approval. |
| 32 | `deef9f7e7b5b61f3f00c9392c8d5fbb75a27978a` | `2026-08-21T04:39:00Z` | `implementation_candidate` | Current portfolio API head carries the synchronized PR31 parent, dimension-scoped portfolio acceptance, 682 tests with 100% statement-and-branch coverage, Ruff, repository validation, and 61 SQL acceptance files; hosted Checks 19 queued and 7 skipped; no formal approval. |
| 31 | `110142f0cc52c835095325426a6edc17a12d9366` | `2026-08-21T04:39:00Z` | `implementation_candidate` | Repaired duplicate projection-receipt fixture identity and status-validator schema gate; 649 tests, 100% statement-and-branch coverage, Ruff, and full PostgreSQL 18 migration/acceptance pass; hosted Checks 19 queued and 7 skipped with no current failure; Draft; no formal approval, merge, release, or deployment claim. |
| 30 | `6026fb4a186f59bc431c087f2ba94fee2bcfe314` | `2026-08-21T04:39:00Z` | `implementation_candidate` | Current ancestor with 614-test/100%-coverage, repository, clean PostgreSQL 18 acceptance, and zero local Semgrep findings; hosted Checks 19 queued and 7 skipped after parent propagation; Draft; no formal approval or protected integration. |
| 29 | `3e9edee4a57e7adde60d96522f29d34f5c95559d` | `2026-08-21T06:08:34Z` | `implementation_candidate` | Current data-management evidence-closure ancestor with the Python support-boundary and uv cooldown repairs; local full Semgrep is zero findings, hosted Checks are queued, and the PR is Ready; no formal approval or protected integration. |
| 27 | `8815b281f1ec5804bc1d2e9a3d210fbc1187e6f1` | `2026-08-21T06:08:34Z` | `implementation_candidate` | Current improvement ancestor; replay-before-liveness and test-isolation fixes pass 542 tests, 100% coverage, repository validation, and clean PostgreSQL 18 acceptance; 25 repository Checks are green and the PR is Ready, with exact-head reviews pending; no protected integration or formal approval. |
| 26 | `a5cfad3419d35246a724da1909c95beb6f9ff3d1` | `2026-08-21T05:11:03Z` | `implementation_candidate` | Current target-state replan head; transaction-isolated planner fixture passes the exact PostgreSQL 18.4 acceptance loop, with 531 Python tests at 100% statement-and-branch coverage, Ruff, and repository validation; hosted Checks queued; Draft; no protected integration or formal approval. |
| 24 | `d19a5e70b9746eb0f4bcfdc27b87d445ac4ec7f8` | `2026-08-21T01:27:22Z` | `implementation_candidate` | Current target-state monitoring head; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; hosted Checks queued; Draft; no protected integration or formal approval. |
| 23 | `88b0d083f1abcb639fab3d17b63166da4428ac78` | `2026-08-21T01:27:22Z` | `implementation_candidate` | Current target-state verification head; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; hosted Checks queued; Draft; no protected integration or formal approval. |
| 22 | `a85e4c6466545369c675f4055de99bd836bc7967` | `2026-08-21T00:21:15Z` | `implementation_candidate` | Current target-state completion ancestor; planner fixture supersession is transaction-isolated, all 29 local PostgreSQL 18.4 SQL acceptance files pass, and hosted Checks are queued after the push; no protected integration or formal approval. |
| 21 | `4ada32a811c2f5ba7ac2138c0826229c5d62e78b` | `2026-08-20T14:22:40Z` | `implementation_candidate` | Repository Checks terminal green; exact-head OpenCode dispatch was accepted; no qualifying independent current-head approval observed. |
| 19 | `6764f5eabfb26c782e2067cf35bc084dca22f2a3` | `2026-08-21T01:27:22Z` | `implementation_candidate` | Current target-state start head; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; hosted Checks queued; Draft; no protected integration or formal approval. |
| 18 | `8562545f6d8c4ebc62e47eab63f86c6b9763f19b` | `2026-08-21T05:23:57Z` | `implementation_candidate` | Documentation snapshot source head; evidence baseline includes the current PR12 projection repair, PR16, scheduler, synchronized PR29→30→31→32→33→35→36 stack, and final local runtime/coverage/PostgreSQL evidence; hosted Checks 10 queued; Draft; no formal current-head approval observed. |
| 17 | `75e2f55b1e24724f007448734abe30f521668ce7` | `2026-08-21T01:27:22Z` | `implementation_candidate` | Current target-state schedule head; full local PostgreSQL 18 SQL acceptance passes after the fixture-order repair; hosted Checks queued; Draft; no protected integration or formal approval. |
| 16 | `8f852ac54b3636d147c37b6c5b652bf7a16e1ee6` | `2026-08-21T00:03:03Z` | `implementation_candidate` | Current target-state approval candidate; fixture-isolation repair passes 231 Python tests with 100% statement-and-branch coverage, Ruff, repository validation, and all 25 real PostgreSQL 18.6 acceptance files; exact-head OpenCode dispatch accepted; hosted Checks queued; no protected integration or formal approval. |
| 15 | `cda7aa69c853d3ea2292c14a47d51eaea4b0fe0d` | `2026-08-20T22:53:58Z` | `implementation_candidate` | Current target-state planner API ancestor; local stack propagation completed and exact-head review dispatch is required; no protected integration or formal approval. |
| 14 | `ca6889497728e1a3f09d68790a9096576e13a3ff` | `2026-08-21T06:08:34Z` | `implementation_candidate` | Unchanged `main` integration candidate; prior `attest-protected-main` run `32036084953` and `installed-process-readiness` run `32036084876` remain historical failures, while attempt-2 reruns are queued; wait for PR34/main integration before rebuilding. |
| 12 | `4f614fb96047fe1d6e844fec4998ac465b09ec06` | `2026-08-21T02:09:43Z` | `implementation_candidate` | Current target-state planner candidate; RED regression reproduced superseded-current projection leakage, the minimal predicate repair preserves historical visibility, and all 22 SQL acceptance files pass on clean PostgreSQL 18.6; hosted Checks 19 queued and 7 skipped; no formal approval, merge, release, or deployment claim. |
| 11 | `f57cf99d4597a610590746d6c316c4a27dc3999a` | `2026-08-21T06:08:34Z` | `implementation_candidate` | Current security-repair head removes committed workflow database credentials, uses run-scoped or generated values at runtime, and exports compose credentials in the generating step; focused tests, actionlint, repository validation, direct Compose configuration, and real PostgreSQL runtime/RLS acceptance pass locally; hosted Checks including Strix are pending, with no formal approval or protected merge. |

## Open issues and control-plane work

| Issue | Evidence-backed action |
| ---: | --- |
| [25](https://github.com/ContextualWisdomLab/enterprise-architecture-core/issues/25) | Convert data-management assessment gaps into evidence-backed improvement initiatives. Keep it linked to the implementation stack and close only after the acceptance evidence exists. |
| [20](https://github.com/ContextualWisdomLab/enterprise-architecture-core/issues/20) | Run repository acceptance on protected `develop` pushes. Verify the three workflow trigger boundaries after integration. |

The hourly organization PR loop belongs to the central `.github` control plane;
central PR [1184](https://github.com/ContextualWisdomLab/.github/pull/1184) at
exact head `d31ed5dd6562a92514a3af1b79c4d832c9dde98d` adds the hourly fallback
but remains unmerged with Checks queued and no current-head approval. This
repository’s product workflows remain responsible for repository,
runtime, and supply-chain evidence. A scheduled run is an invocation signal,
not a merge authorization. The loop must preserve the sequence
`review → repair → Checks → current-head gate → protected merge → next work`.

## Prioritized buyer gaps

| Priority | Gap | Current evidence | Buyer impact | Smallest next slice | Verified when |
| --- | --- | --- | --- | --- | --- |
| P0 | Protected integration truth is behind the implementation candidate | At `2026-08-20T13:06:28Z`, protected `develop@1c0fa8b15ceb9e72186274aeb255d6777eb84ef4` is the initialization baseline and `main@ca6889497728e1a3f09d68790a9096576e13a3ff` is an unmerged source branch; PRs #14 and #18 explicitly record stale-base risk | A buyer cannot tell which decision surface can be installed today. | Complete the exact-head review/Checks/merge loop for the stack root, then rebuild dependent PRs from the resulting protected SHA. | Protected target SHA contains the intended runtime/contracts, all required workflows are terminal green, and the target branch ruleset/review evidence is current. |
| P0 | No immutable customer release is observed | At `2026-08-20T13:06:28Z`, GitHub release/tag inventory is empty; package/SBOM workflows exist only as candidate evidence | A buyer cannot pin, install, verify, or roll back a product version. | Publish the first versioned package after protected integration and update `CHANGELOG.md` with the exact acceptance evidence. | Release tag, package checksums/SBOM/provenance, install smoke test, and rollback instructions all point to the same commit. |
| P0 | Shared Context Graph contract is release-gated rather than live-proven | At `2026-08-20T13:06:28Z`, `/ready` intentionally fails closed when the exact `cwl-context-contracts` distribution is unavailable; no immutable contract version or live positive readiness evidence is observed | Cross-product impact decisions cannot be promoted to production interoperability without a trusted contract artifact. | Publish or consume the exact immutable contract release through the approved connector boundary; keep unknown/mutable branches rejected. | Live `/ready` is 200 with the exact contract version, and cross-domain replay/tenant/authority acceptance passes against the released artifact. |
| P1 | Portfolio fit/scoring is normalized but not a buyer API | PR [32](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/32) at exact head `deef9f7e7b5b61f3f00c9392c8d5fbb75a27978a` adds the authenticated single-object assessment read port; synchronized PR [33](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/33) at exact head `e157633e322098a78ddba8db8a283aeaf2de7482` adds the deterministic summary candidate | A portfolio owner still needs an aggregate fit, criticality, cost, and risk answer on the protected branch. | Complete the current-head review and Checks loop for #32, then repeat it for the synchronized summary while preserving tenant, valid-time, recorded-time, truth status, evidence, and next-action fields. | The integrated summary has an OpenAPI contract, purpose-bound reader, deterministic PostgreSQL acceptance, negative authorization tests, and a current-head runtime response. |
| P1 | Append-only database write hot spots lack buyer-observed capacity evidence | PR [35](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/35) at exact head `d8d0cc71b099c71d30fd40d7b7bd1adfefb227f0` adds migration 0050, ADR 0025, deterministic 16-bucket tenant routing, fillfactor headroom, hot-write indexes, and clean/upgrade PostgreSQL acceptance; PR [36](https://github.com/ContextualWisdomLab/enterprise-architecture-core/pull/36) at exact head `ee9d5bcb38507b32c86486dce3480733ab72c4ce` adds a repeatable tenant-scoped capacity snapshot, failure-safe context restoration, and operator runbook; physical partitions and production skew measurements remain absent | A buyer cannot yet distinguish a measured high-write operating envelope from a schema prepared for future scale. | Complete the exact-head review/Checks loop for PR36, then compare authorized representative-data snapshots for tenant skew, queue lag, write amplification, and index behavior before proposing a physical HASH/LIST cutover. | Protected integration and a repeatable PostgreSQL capacity report bind the same migration, measurements, RLS behavior, and rollback evidence; no production capacity claim is made before then. |
| P1 | External lifecycle and data/AI adapters remain contract catalog entries | Connector catalog and receipt guards exist; vendor lifecycle and owner-produced production adapters are explicitly future work | Buyers see a safe integration boundary but still assemble feeds manually. | Add one highest-leverage REST/event adapter with canonical URI, receipt digest, replay, tenant, truth-origin, and failure-retry evidence. | The owning external system, released connector contract, real inbound receipt, replay test, and failure recovery are observed together. |
| P1 | Decision results are headless and lack an accessible buyer presentation surface | Storybook inventory explicitly records no visual UI | A non-technical buyer cannot yet explore capability maps, scenario comparison, or transformation timelines without a consuming product. | First approve a presentation-module boundary and repeated object inventory; then create Figma file/ADR linkage and Storybook tokens/components. | Browser E2E proves keyboard, screen-reader-equivalent text, exact-value alternatives, i18n consistency, and action edge cases against live API data. |
| P1 | CSAP/SOC 2 readiness needs protected, operational, and independent evidence | [ADR 0006](adr/0006-security-control-evidence-boundary.md) and [`docs/doctoring/CSAP-SOC2-CONTROL-EVIDENCE.md`](doctoring/CSAP-SOC2-CONTROL-EVIDENCE.md) now map preparation areas to NIST CSF 2.0, AICPA Trust Services Criteria, and the Korean CSAP governing rule; implementation evidence remains on unmerged candidates and no certification or audit report is claimed | A regulated buyer can inspect the evidence boundary and missing work, but cannot yet treat the repository as an audit-ready service pack. | Re-run every mapped control against the same protected/released service boundary, add operational period/population/exception records, and engage the applicable independent assessor before making a certification or attestation claim. | Every claimed control has current executable or operational evidence, defined scope and cadence, retained exceptions, and assessor-confirmed evidence where required; missing evidence remains explicitly `planned`, not `compliant`. |

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
- The Korean CSAP governing rule for the preparation boundary; certification
  type, grade, and assessment scope must be confirmed with the applicable
  authority before an application.

The current preparation crosswalk is [CSAP-SOC2-CONTROL-EVIDENCE.md](doctoring/CSAP-SOC2-CONTROL-EVIDENCE.md).

All references in implementation ADRs and this baseline use APA 7th form. A
standard is not a conformance claim: the corresponding row must point to
current executable, runtime, or audit evidence.
