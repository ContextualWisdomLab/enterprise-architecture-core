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
- exact issuer/audience/JWKS validation;
- immutable or append-preserving audit evidence;
- bounded relation traversal;
- schema and payload size limits;
- connector egress allowlists;
- no secrets or raw PII in events;
- explicit review before inferred/proposed assertions become authoritative.
