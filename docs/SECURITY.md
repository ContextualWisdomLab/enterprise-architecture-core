# Security Architecture

## Assets

- architecture inventory and business-criticality decisions;
- technology lifecycle and vulnerability-impact evidence;
- transformation scenarios, target-state decisions, and immutable approval history;
- identity links, decision actors/reasons, transactional outbox, and audit history.

## Threat boundaries

- Keyverse token verification and operation-specific role boundary;
- service-to-database purpose-bound read/command boundary;
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
- planner and approval endpoints verify a Keyverse RS256 access-token signature,
  exact issuer, service audience, integer expiration, tenant UUID, and the
  operation-specific allowed role before entering a database boundary;
- planner reads use `EA_READ_ROLES`; target-state approval uses the separate
  `EA_APPROVAL_ROLES` allow-list so read authority cannot silently become write
  authority;
- Keyverse JWKS retrieval is configuration-bound to HTTPS under the exact issuer
  origin/path, rejects redirects, uses a bounded response and timeout, rejects
  malformed/ambiguous JSON, and selects exactly one signing key by `kid`;
- `ea_runtime` receives execute privilege only on the purpose-bound
  `read_technology_target_state_plan(...)` read wrapper and
  `approve_target_state(...)` command wrapper. Both are `SECURITY DEFINER` with
  fixed `pg_catalog` search paths, bind the verified tenant transaction-locally,
  and expose no direct table or underlying-projector privilege;
- the approval API accepts no caller-supplied actor field. EA Core derives the
  audit actor from the verified Keyverse issuer and subject, requires UUIDv7
  decision/evidence/transformation identifiers, explicit effective time and a
  bounded human reason, and uses the decision request as the idempotency key;
- exact approval replay returns the original immutable receipt while reuse of
  the same decision request for different meaning fails closed;
- authoritative approval history and the privacy-minimized
  `org.contextualwisdomlab.ea.transformation.approved.v1` outbox event commit in
  the same PostgreSQL transaction; neither can be left behind alone;
- outbound approval events omit private actor/reason text and carry only the
  references required for deterministic downstream handling;
- DSN credentials are translated into documented libpq environment variables,
  including `PGSSLSNI` for `sslsni`, and are not placed in the `psql` argument
  vector or returned in API errors;
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
- no secrets or unnecessary raw personal attributes in events;
- purpose-bound access instead of masking accountability identifiers:
  Keyverse `iss` plus `sub`, tenant, actor, purpose/reason and evidence remain
  available to authorized audit workflows while raw names, emails, credentials,
  and access tokens stay outside EA event/context bundles;
- explicit human review before inferred/proposed assertions become authoritative.

## Fail-closed behavior

Missing or partial OIDC configuration disables protected decision endpoints
instead of accepting anonymous traffic. Missing/invalid bearer credentials
return only stable error codes and a buyer next action. Missing approval-role
configuration disables the mutation boundary rather than inheriting read roles.
Database/query/command-port failure keeps the decision pending at 503; it never
falls back to direct SQL, cached model judgment, or a synthetic approval receipt.
