# ADR 0010: Treat quality evidence as a release gate

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Production statement and branch coverage, public docstrings, migration
rehearsal, contract tests, security checks, SBOM, provenance, and operational
runbooks are release requirements.

## Consequence

A feature is not considered releasable merely because its happy-path code
exists.

The primary exact-head package SBOM remains SPDX 3.0.1. The pinned GitHub
`actions/attest` v4.2.2 automatic SBOM detector accepts SPDX JSON documents
identified by the SPDX 2.x `spdxVersion` and `SPDXID` fields, while the canonical
SPDX 3.0.1 JSON-LD uses `@context` and `@graph`. Rather than generate a second,
weaker-format compatibility SBOM, protected `main` uses the action's explicit
custom-predicate mode to sign the canonical SPDX 3.0.1 document directly with
in-toto predicate type `https://spdx.dev/Document/v3`.

Package evidence is admitted as one exact bundle: one wheel, one source
distribution, the canonical SPDX document, and one checksum manifest naming
exactly those three evidence files. The verifier rejects symlinks, mixed or
extra distributions, malformed checksum identities, checksum drift, malformed
SPDX evidence, and platforms that cannot provide no-follow file semantics. The
same verifier runs on the generated bundle before upload and again after the
protected-main job downloads it, before any attestation is created. Download
success therefore never substitutes for package-evidence admission.

The protected-main job then verifies both SLSA provenance and SPDX 3
attestations against the exact repository, `refs/heads/main`, source SHA,
signer-workflow path, signer digest, GitHub OIDC issuer, hosted-runner policy,
artifact SHA-256, and canonical SPDX meaning, and retains the machine-readable
verification results under an exact-SHA artifact name. Attestation verification
remains release evidence only; it does not replace independent review, package
identity, migration/rollback acceptance, or publication authorization.
