# ADR 0007: Separate evidence, truth origin, and confidence

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Material revisions and relationships may reference exact evidence digests and
carry authoritative, observed, inferred, proposed, superseded, or rejected
truth status. Confidence remains a domain-specific assessment, not a truth
status.

## Consequence

LLM and LineageWeave proposals cannot silently enter authoritative audit views.
