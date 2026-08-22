# Security Architecture

## Assets

- architecture inventory and business-criticality decisions;
- technology lifecycle and vulnerability-impact evidence;
- transformation scenarios and target-state decisions;
- identity links and audit history.

## Threat boundaries

- Keyverse token verification boundary;
- service-to-database boundary;
- inbound evidence and event boundary;
- outbox publication boundary;
- graph/read-model projection boundary.

## Required controls

- least-privilege database roles;
- tenant-scoped API enforcement, composite tenant foreign keys, and forced
  PostgreSQL row-level-security policies;
- no direct application-table privilege for the `ea_runtime` login: arbitrary
  PostgreSQL custom GUC values are caller-controlled metadata and therefore do
  not confer tenant authority;
- the implemented target-state planner verifies a Keyverse RS256 access-token
  signature, exact issuer, service audience, integer expiration, tenant UUID,
  and allowed EA read role before entering the database query boundary;
- Keyverse JWKS retrieval is configuration-bound to HTTPS under the exact issuer
  origin/path, rejects redirects, uses a bounded response and timeout, rejects
  malformed/ambiguous JSON, and selects exactly one signing key by `kid`;
- `ea_runtime` receives execute privilege only on the purpose-bound
  `read_technology_target_state_plan(...)` wrapper. The wrapper is
  `SECURITY DEFINER` with a fixed `pg_catalog` search path, binds the verified
  tenant transaction-locally, calls the fully qualified projector, and exposes
  no direct table or projector privilege;
- DSN credentials are translated into libpq environment variables and are not
  placed in the `psql` argument vector or returned in API errors;
- UUIDv7 checks on owned identities and exact canonical URI binding to tenant,
  object type, and object ID;
- non-overlapping active intervals for Keyverse links, object revisions,
  architecture relations, and lifecycle phases;
- relation endpoint type validation before a fact becomes authoritative;
- object-shaped outbox payloads and validated projection source/event identity;
- immutable or append-preserving audit evidence;
- bounded relation traversal;
- schema and payload size limits;
- connector egress allowlists;
- no secrets or raw personal attributes in events;
- purpose-bound access instead of masking accountability identifiers:
  Keyverse `iss` plus `sub`, tenant, actor, and purpose remain visible to
  authorized reviewers because masking those fields would stop audit and
  command authorization; raw names, emails, credentials, and access tokens stay
  outside EA event/context bundles;
- explicit review before inferred/proposed assertions become authoritative.

## Fail-closed behavior

Missing or partial OIDC configuration disables the planner instead of accepting
anonymous traffic. Missing/invalid bearer credentials return only stable error
codes and a buyer next action. Database or query-port failure keeps the decision
pending at 503; it never falls back to direct SQL or cached model judgment.
