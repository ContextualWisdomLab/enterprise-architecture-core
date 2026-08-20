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
`actions/attest` v4.2.2 parser currently accepts SPDX JSON documents identified
by `spdxVersion` and `SPDXID`, so protected-main attestation uses a separately
generated, checksummed SPDX 2.3 predicate while retaining the SPDX 3.0.1
artifact as the canonical package evidence. The two artifacts must never be
treated as interchangeable or left outside the exact-head checksum manifest.
