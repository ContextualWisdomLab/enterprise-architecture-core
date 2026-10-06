# Repository Actions and local gates

Scope: **enterprise-architecture-core** only. Organization-required workflows
remain owned by `ContextualWisdomLab/.github`; this change neither copies them
nor changes their runner groups, allowlists, branch rules or review authority.

## Source and requirements

- Product acceptance: `../docs/PRD.md`, `../AGENTS.md`, `../docs/TEST_STRATEGY.md`.
- PR #21 (`7231e58cd10d55c936ca08fb4f806af2a23bf247`) owns exact source
  checkout and `{develop, main}` integration triggers; this lane is stacked on
  that proposal. The protected/default branch transition is issue #20 / central
  `.github#1137`, not permission to merge into currently unprotected `main`.
- PR #34 (`3f5797568f8e172061b41bd35b69655fb0cfc68b`) owns canonical
  package/DSSE validation and reproducibility. This lane preserves the baseline
  SPDX/checksum gate, **not** that PR's stronger unmerged verifier. Do not claim
  release readiness before reconciling its hosted-runner provenance policy.
- Descendant SQL acceptance order (notably PR #30) stays serial. PR #39/#40 and
  API/database issues #46/#47 are separate owners, not silently merged features.

## Runner admission — provisioning required

Every executable local job requires Linux x64 `self-hosted` plus `ea-core-ci`.
Attestation additionally routes to **a separate** `ea-core-release-ci` pool and
runs only on a protected `main` push. These custom labels are an explicit
provisioning contract, **not existing verified capacity**.

Live inventory on 2026-10-05 KST found ten organization runners, nine online,
with no `ea-core-ci` or `ea-core-release-ci` labels. Repository-local inventory
was empty. Existing central control/security and private health/Gyeot runner
restrictions must stay unchanged; do not relabel or borrow them to clear a queue.

Before publishing/executing these workflows, the runner owner must:

1. Provision disposable per-job Linux x64 machines with no production mounts,
   private-network routes, unrelated secrets or host Docker socket access.
   Docker inside the disposable machine is required for service containers.
2. Create separate candidate/release groups restricted to this repository and
   applicable workflow refs; assign only the matching label. Labels alone are
   not isolation or a security certification. Record actual group membership
   and selected-repository/workflow restrictions.
3. Install Bash 4+, Docker Engine and Compose v2, PostgreSQL client 18,
   Git, curl, GNU coreutils (`sha256sum`, `sed`), Python setup prerequisites.
   Setup actions install Python 3.11–3.14 and uv **0.11.32**; action SHA pins,
   read-only default permissions and checkout credential suppression remain.
4. Preserve fork PR admission controls: each candidate job first runs an inline
   repository-identity check, explicitly failing foreign sources before checkout
   or any action/local script. Do not skip these jobs: skipped required checks can
   report success without running their gates. Same-repository PR code is still
   code execution: trusted collaborator review and disposable infrastructure are
   required. Never switch to `pull_request_target` plus untrusted head checkout.
5. Verify exact-head Actions runs, each job's runner name, selected group,
   conclusion and uploaded evidence. Local tests and `actionlint` are not this
   operational proof. Do not weaken protected checks or synthesize approvals.

## Local gates

Run from a source checkout with the pinned uv executable on PATH:

```sh
bash .github/scripts/ci.sh validate 3.14
bash .github/scripts/ci.sh postgres-migration  # disposable database PG* required
bash .github/scripts/ci.sh compose-runtime
bash .github/scripts/ci.sh runtime-readiness
bash .github/scripts/ci.sh package
bash .github/scripts/validate-sbom.sh /absolute/fresh/dist
```

Generate a local SBOM with the same `syft 1.51.0` before `validate-sbom.sh`:

```sh
syft scan dir:/absolute/fresh/dist -o spdx-json@3.0=/absolute/fresh/dist/enterprise-architecture-core.spdx.json
```

Python gates preserve compilation, Ruff/public docstrings, all pytest tests,
100% production statement/branch coverage and public repository validation.
CI-owned tests in `.github/tests` must be executed explicitly alongside `tests`
because project `testpaths` does not implicitly discover hidden directories.

Database gates preserve clean migrations, idempotency, checksum rejection,
previous-boundary upgrades, atomic rollback and every SQL fixture. CI-only
Compose uses a unique project, fresh volume and dynamic loopback host port;
cleanup is scoped to that project, never the developer/production Compose stack.
Installed-process checks preserve independent database/immutable-contract
readiness dimensions; absence of a released contract remains HTTP 503.

Packages are built in a fresh temporary directory and installed into an
isolated venv; one wheel and one sdist are required. Fixed workspace `dist` is
never consumed. Successful package builds retain the printed directory for
artifact/SBOM use; remove that specific temporary directory when finished.
No tag, release, publication, merge or upstream integration is performed by a
local gate.

## Execution status

Baseline from PR #21: 126 Python tests and 100% production statement/branch
coverage executed locally before changes. Actual self-hosted Actions execution,
runner provisioning, protected-main convergence and PR #34 release-evidence
integration remain separate required gates. A localhost package or test result
must not be reported as a production deployment or accepted architecture fact.
