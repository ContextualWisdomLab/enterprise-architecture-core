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
