# Technical Requirements Document

## Runtime direction

The eventual service will use PostgreSQL as its canonical write model, a
stateless API tier, a transactional outbox publisher, and derived graph/read
models. This initial foundation intentionally ships contract and schema
artifacts before a runtime framework is selected.

## Storage requirements

- PostgreSQL 18-compatible SQL.
- UUIDv7 identifiers.
- Third-normal-form tables with explicit foreign keys.
- Distinct valid-time and system-time fields.
- Historical changes close intervals; they do not overwrite history.
- Every table, index, and named constraint uses two or more snake-case words.
- Graph projections are disposable and rebuildable from authoritative events.

## Identity and authorization

Keyverse is the identity authority. Runtime implementations must verify:

1. JWT signature against configured JWKS.
2. Exact issuer.
3. Intended audience.
4. Expiration and not-before constraints.
5. Tenant claim.
6. Role/permission claim.

The service stores opaque Keyverse subject links only. Email addresses and
credentials are not identity keys.

## Event requirements

- CloudEvents structured JSON.
- Transactional write and outbox insertion in the same database transaction.
- Idempotent consumers using source plus event identifier.
- Opaque references, not secrets or raw personal information.
- Payload schema versions and SHA-256 evidence references.

## Failure behavior

- Malformed contracts fail closed.
- Cross-tenant references are rejected.
- Projection failures do not roll back the authoritative transaction.
- Repeated publication failures remain visible and retriable.
- Inferred or proposed assertions cannot become authoritative by parsing alone.
