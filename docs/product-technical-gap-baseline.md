# Enterprise Architecture Core product and technical gap baseline

This ledger records executable gaps for `ContextualWisdomLab/enterprise-architecture-core`. It is not release evidence and does not promote mutable pull-request state, product analysis, security verdicts or model output into authoritative architecture truth.

## Product boundary

`enterprise-architecture-core` is the EA Decision Plane. It owns business capability, application, interface, technology/provider/version, organization context, typed temporal relations, lifecycle and portfolio assessment, objectives, initiatives, transformations and delta-based scenarios. Core, Supporting and Generic responsibilities remain explicit through bounded contexts, ACLs and minimal Shared Kernels.

Foreign product truth stays with its producer. EA consumes released versioned contracts and retains source authority, event identity, schema/profile/admission version, valid/business time, system-recorded time and provenance. Direct foreign application-table access and cross-service SQL are prohibited.

## Current integration and evidence gaps

The intended integration/release authority is protected `main`, but live repository metadata still reports `develop` as default and the accepted `main` line has not become the protected/default authority. Organization ruleset repair and branch migration therefore remain central control-plane dependencies. Routine administrator bypass, self-approval, synthetic human review and stale/predecessor evidence are not merge evidence.

The current integration-workflow root has repaired a source-integrity defect: PR CI, PostgreSQL migration, runtime-readiness and supply-chain jobs now bind checkout and an explicit post-checkout equality check to the PR source SHA, while dependency/package artifact identities use that same source identity. Previous workflow successes are predecessor evidence after the head moved. The current exact head still requires fresh materialized terminal CI/security/PostgreSQL/package/SBOM/provenance/review evidence.

An immutable release from protected `main` remains outstanding for the current EA changes. Release authority requires one exact integrated source revision whose database migrations, RLS/tenant isolation, package smoke, security checks, SBOM, provenance/attestation, rollback and release artifacts all agree.

## Context Fabric and quarantine dependencies

EA may project Context Assertion data only after `ContextualWisdomLab/context-graph-contracts` publishes a compatible immutable release with schema/profile/admission/conformance and provenance evidence. Mutable CGC pull requests are development evidence, not production authority.

The Quarantine Sandbox Runtime is an independently deployable/reusable producer. Its EA-facing authority is isolation-runtime and artifact-analysis evidence. `contextual-orchestrator` owns caller/application/task/tool authorization and user actions; Wardnet owns gateway/SOC policy, maliciousness verdict, incidents, quarantine/block/notification/retention.

EA may represent Quarantine Sandbox Runtime application-service/API/backend identity, container/runtime/security technology and provider/version, lifecycle, ownership, architecture-risk context, remediation, transformation and attestation provenance through the released CGC ACL. A malware verdict or artifact risk score must never become an authoritative EA architecture fact. Direct database coupling and source copying are prohibited.

Required directional interactions remain `ContextualWisdomLab/contextual-orchestrator -> quarantine application-service lease` and `ContextualWisdomLab/wardnet -> quarantine artifact-analysis/evidence` where supported by released producer contracts. The current quarantine integration PR remains provisional and Draft until its parent lineage, CGC release dependency and exact-head gates are clean.

## Next executable closure

1. Central owner protects `main` to the intended integration/release standard, switches the default only after protection is verified, and rereads effective `~DEFAULT_BRANCH` rules.
2. Central owner replaces only the structurally impossible solo-maintainer approval count/routine bypass while preserving deterministic checks, security, thread resolution, deletion and non-fast-forward protection.
3. Rebuild the EA dependency root and descendants non-force from fresh protected `main`, preserving valid child deltas and resetting all predecessor evidence.
4. Reacquire exact-source Python/PostgreSQL/RLS/runtime/package/SBOM/provenance/security/review evidence on every moved head.
5. After a protected immutable CGC Context Assertion release exists, rebuild the Quarantine Sandbox Runtime projection so receipt identity, source authority, schema/profile/admission version and provenance remain fail-closed and foreign verdict authority cannot leak into EA.
