# ADR 0006: Delegate identity to Keyverse

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Keyverse supplies OIDC identity and role claims. The repository stores opaque
subject links only and verifies signature, issuer, audience, expiry, tenant, and
role.

## Consequence

Credentials and federation state are not duplicated in the EA database.
