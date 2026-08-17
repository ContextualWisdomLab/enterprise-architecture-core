# ADR 0007: Separate evidence, truth origin, and confidence

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Material revisions and relationships may reference exact evidence digests and
carry authoritative, observed, inferred, proposed, superseded, or rejected
truth status. Confidence remains a domain-specific assessment, not a truth
status.

Temporal uniqueness applies to current authoritative revisions and relations,
not to assertions with a different truth origin. An observed, inferred, or
proposed assertion may therefore overlap the validity interval of an
authoritative fact so evidence can be compared before an explicit decision.
Two overlapping current authoritative assertions for the same governed fact
remain invalid.

## Consequence

LLM and LineageWeave proposals cannot silently enter authoritative audit views.
Review workflows can retain conflicting proposals and observations without
mutating the authoritative record, then accept, reject, or supersede them
through an explicit governed command.
