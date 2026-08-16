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

This initial pull request establishes the reviewed product boundary, 3NF schema,
OpenAPI/AsyncAPI contracts, Keyverse OIDC boundary, lifecycle and outbox model,
security baseline, and ten architecture decisions. Runtime CRUD services are a
separate implementation milestone.

## Validation

```bash
uv sync --extra dev
uv run --extra dev python -m coverage run -m pytest -q
uv run --extra dev python -m coverage report
uv run --extra dev python scripts/validate_repository.py
```
