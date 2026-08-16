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
  not confer tenant authority; future domain commands and queries must bind
  verified Keyverse issuer, audience, tenant, and role claims at a purpose-bound
  service/function boundary before database access is granted;
- UUIDv7 checks on owned identities and exact canonical URI binding to tenant,
  object type, and object ID;
- non-overlapping active intervals for Keyverse links, object revisions,
  architecture relations, and lifecycle phases;
- relation endpoint type validation before a fact becomes authoritative;
- object-shaped outbox payloads and validated projection source/event identity;
- exact issuer/audience/JWKS validation;
- immutable or append-preserving audit evidence;
- bounded relation traversal;
- schema and payload size limits;
- connector egress allowlists;
- no secrets or raw PII in events;
- explicit review before inferred/proposed assertions become authoritative.
