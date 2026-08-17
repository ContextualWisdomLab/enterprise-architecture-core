# ADR 0019: Authenticate the target-state planner at the Keyverse and database boundaries

- **Status:** Accepted for the active PR; not protected-default-branch shipped truth until integration.
- **Date:** 2026-08-17

## Context

The Technology Change Impact & Target-State Planner is already a deterministic, tenant-scoped, bitemporal Enterprise Architecture projection. A buyer-facing read API must expose that decision evidence without turning a caller-controlled PostgreSQL session variable into identity, duplicating Keyverse as an identity provider, granting the runtime login application-table authority, or copying pg-erd-cloud, Semantic Data Portal, or LineageWeave state into EA Core.

JWT verification is security-sensitive. An implementation that merely parses claims, accepts an arbitrary algorithm, ignores an unsupported critical JWS extension, follows JWKS redirects, ignores issuer/audience/expiration, or treats an inferred tenant string as authority would convert untrusted input into an architecture decision boundary. Likewise, giving `ea_runtime` direct table or underlying-projector privileges would let a client bypass the verified HTTP boundary.

## Decision

EA Core exposes `GET /v1/technology-target-state-plans/{technology_version_id}` as a read-only decision endpoint. Every request supplies explicit `valid_at` and `recorded_at` timestamps and a bounded planning horizon so the buyer sees one reproducible real-world/system-recording view.

Keyverse remains the identity authority. The service accepts only an RS256 bearer with one `kid` and verifies the signature against the configured Keyverse JWKS. It verifies the exact issuer, EA Core audience, integer expiration, optional not-before time, non-empty subject, tenant UUID, and an allow-listed EA read role before database access. EA Core implements no JWS critical protected-header extensions, so the presence of `crit` is rejected fail-closed rather than silently ignored. JWKS configuration is fail-closed: HTTPS is mandatory, the endpoint must remain under the configured issuer origin and path, redirects are rejected, response size and timeout are bounded, JSON is strict, and one unambiguous signing key must match the token `kid`.

The PostgreSQL login remains deliberately weak. `ea_runtime` has no direct application-table privilege and no execute privilege on `project_technology_target_state_plan(...)`. It receives only `read_technology_target_state_plan(...)`, a `SECURITY DEFINER` wrapper with a fixed `pg_catalog` search path. The wrapper accepts the already verified tenant UUID, binds it transaction-locally, and calls the fully qualified tenant-scoped projector. Database configuration is translated into libpq environment variables so passwords and DSNs are not placed in the `psql` argument vector.

The API never mutates architecture state, never promotes inferred/proposed evidence, never performs direct foreign-product SQL, and never substitutes LLM/model judgment for deterministic authorization or planner logic.

## Consequences

A missing or partial Keyverse configuration, unsupported or malformed JWS critical extension, unsafe JWKS location, network/key/signature failure, invalid issuer/audience/time/tenant/role claim, malformed bitemporal query, or database/query-port failure is non-passing. The service returns a stable error code and actionable next step without exposing token, DSN, SQL, or credential material.

The design intentionally does not create a generic identity service, token cache, trust registry, command endpoint, or workflow engine. Future mutating EA APIs require a separate decision covering actor/purpose/reason, human review where applicable, idempotency, immutable audit/outbox evidence, and command-specific authorization.

## Primary basis

- OpenID Foundation. (2014). *OpenID Connect Core 1.0 incorporating errata set 2*.
- Internet Engineering Task Force. (2015). *JSON Web Signature (JWS)* (RFC 7515).
- Internet Engineering Task Force. (2015). *JSON Web Token (JWT)* (RFC 7519).
- Internet Engineering Task Force. (2015). *JSON Web Key (JWK)* (RFC 7517).
- Internet Engineering Task Force. (2020). *JSON Web Token Best Current Practices* (RFC 8725).
- PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row security policies* and function security guidance.
- ContextualWisdomLab/keyverse. (2026). *README* and *Relying-party onboarding*.

## Executable evidence

- `src/ea_core_foundation/authorization.py`
- `src/ea_core_foundation/service.py`
- `database/migrations/0021_target_state_plan_query_port.sql`
- `database/init/003_grant_runtime_access.sql`
- `contracts/openapi.json`
- `tests/test_target_state_api.py`
- `tests/test_authorization_hardening.py`
- `tests/test_jws_critical_headers.py`
- `tests/test_planner_failure_paths.py`
- `database/tests/zzzz_verify_target_state_query_port.sql`
- `tests/test_openapi_runtime_surface.py`
