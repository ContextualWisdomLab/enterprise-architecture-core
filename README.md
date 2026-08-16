# Enterprise Architecture Core

`enterprise-architecture-core` is the authoritative enterprise architecture and
transformation decision plane for the ContextualWisdomLab ecosystem.

It records business capabilities, applications, interfaces, technology
components, lifecycle intervals, evidence, and transactional events. It is not
a data catalog, physical database designer, project-management tool, or graph
projection service.

## Initial bounded context

```text
Business Capability
        ▲ supports
Application ── uses ──► Technology Component
        │
        └── exposes/consumes ──► Application Interface
```

The canonical write model is normalized PostgreSQL. Graph views and cross-domain
impact projections are derived consumers. `semantic-data-portal` remains the
Data/AI Context system of record; `pg-erd-cloud` remains the physical schema
evidence producer.

## Repository status

This repository establishes the reviewed product boundary, 3NF schema,
OpenAPI/AsyncAPI contracts, Keyverse OIDC boundary, lifecycle and outbox model,
security baseline, and accepted architecture decisions. The database foundation
also enforces UUIDv7 identity, canonical URI consistency, governed relation
endpoint types, non-overlapping active intervals, tenant RLS as defense in
depth, and transactional outbox rollback through executable PostgreSQL
acceptance. The documented `ea_runtime` login intentionally has no direct
application-table privilege because caller-set PostgreSQL custom settings are
not authorization evidence. Runtime domain commands and queries remain a
separate implementation milestone and must bind verified Keyverse claims before
receiving purpose-bound database authority.

The installable distribution is `enterprise-architecture-core`. Start the
process, call `GET /health`, then call `GET /ready` before sending traffic.

## Run the process surface

```bash
uv sync --extra dev --locked
uv run --extra dev ea-core
```

The process binds `0.0.0.0:$PORT`. After `GET /health` returns `alive`, call
`GET /ready`. A 503 means inspect `contract_ready` and `database_ready` and
repair that dependency before adding the instance to a load balancer.

## Validation

```bash
uv sync --extra dev --locked
uv run --extra dev python -m coverage run -m pytest -q
uv run --extra dev python -m coverage report
uv run --extra dev python scripts/validate_repository.py
```
