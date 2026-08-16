# ADR 0003: Use authority-scoped canonical references

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Cross-product references use UUIDv7-backed CWL URNs defined by
`context-graph-contracts`. Provider IDs and emails are external keys, not
canonical identities.

## Consequence

Ownership is visible in each reference and migration between providers does not
change enterprise identity.
