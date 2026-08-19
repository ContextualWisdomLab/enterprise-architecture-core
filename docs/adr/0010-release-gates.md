# ADR 0010: Treat quality evidence as a release gate

- **Status:** Accepted
- **Date:** 2026-08-16
- **Updated:** 2026-08-19

## Decision

Production statement and branch coverage, public docstrings, migration
rehearsal, contract tests, security checks, SBOM, provenance, and operational
runbooks are release requirements.

A cross-product Context Graph dependency is release-admissible only when all of
the following are true for one unchanged dependency candidate:

1. the dependency state is `immutable-release`, with exact semantic version,
   release tag, and source commit identity;
2. the reviewed environment installs that exact `cwl-context-contracts`
   distribution version and every contract resource consumed by EA Core exists;
3. an independently approved `cwl-context-bundle-manifest/v1` is retained with
   the EA dependency declaration; and
4. the installed provider package's own
   `verify_packaged_contract_bundle_manifest()` verifier confirms that the
   approved manifest matches the complete installed contract bundle byte for
   byte.

Version equality, resource presence, a plausible commit SHA, or a mutable PR
head is insufficient release evidence. Complete-bundle verification also does
not replace source/artifact provenance, SBOM attestation, authorization, formal
review, or protected-branch evidence; those remain separate gates.

The verifier is consumed from `context-graph-contracts` rather than duplicated
inside EA Core so package hashing and bundle semantics remain owned by the
contract provider. While the dependency manifest names a provisional PR head,
`approved_bundle_manifest` remains null and protected integration fails closed.

## Consequence

A feature is not considered releasable merely because its happy-path code
exists. A consumer also cannot promote an unreleased or byte-drifted contract
bundle by filling in release-looking metadata; it must retain independently
approved complete-bundle evidence and satisfy every separate release gate on
the exact integrated heads.
