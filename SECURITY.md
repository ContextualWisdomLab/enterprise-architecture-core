# Security Policy

## Trust boundary

The service accepts Keyverse-issued bearer tokens. Implementations must verify
signature, issuer, audience, expiration, and tenant/role claims against a pinned
configuration. Email addresses are not identity keys and credentials are never
stored in this database.

## Data controls

- Tenant isolation is enforced at the API and PostgreSQL layers.
- Event payloads contain opaque references, not credentials or raw personal
  information.
- Evidence digests prove byte identity but do not establish authorization.
- Imported and inferred records enter a review queue before authoritative use.
- Relation traversal must enforce bounded depth and approved relation types.

Report vulnerabilities privately to the organization maintainers.
