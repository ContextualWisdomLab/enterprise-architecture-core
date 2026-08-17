# Enterprise Architecture Core

`enterprise-architecture-core` is the authoritative enterprise architecture and
transformation decision plane for the ContextualWisdomLab ecosystem.

It records business capabilities, applications, interfaces, technology
components, lifecycle intervals, evidence, portfolio assessments, architecture
objectives/initiatives, target-state scenarios, and transactional events. It is
not a data catalog, physical database designer, project-management tool, or
runtime graph-projection service.

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

The current development stack establishes the reviewed product boundary, 3NF
schema, OpenAPI/AsyncAPI contracts, Keyverse OIDC boundary, lifecycle and outbox
model, normalized portfolio assessment, versioned architecture objectives and
remediation initiatives, and immutable-baseline target-state scenarios. Scenario
projection can now compare object and typed-relation presence without mutating
authoritative architecture facts; requested-present relations whose projected
source or target is absent are retained as evidence but cannot appear active.

The database foundation enforces UUIDv7 identity, canonical URI consistency,
governed relation endpoint types, non-overlapping active intervals, tenant RLS
as defense in depth, provenance requirements for authoritative/observed facts,
and transactional outbox rollback through executable PostgreSQL acceptance.
The documented `ea_runtime` login intentionally has no direct application-table
privilege because caller-set PostgreSQL custom settings are not authorization
evidence. Runtime domain commands and queries remain a separate implementation
milestone and must bind verified Keyverse claims before receiving purpose-bound
database authority.

The installable distribution is `enterprise-architecture-core`. Start the
process, call `GET /health`, then call `GET /ready` before sending traffic.

## Target-state scenario evidence

A scenario binds one immutable real-world/system-recording baseline and ordered,
append-preserving object/relation deltas. `project_scenario_objects(uuid)` gives
the final object-presence view. `project_scenario_relations(uuid)` reconstructs
baseline authoritative relations, overlays the latest active relation intent,
and composes it with final object presence so the target state has no silently
dangling active edge. These projectors are decision-plane evidence; they do not
write another product's store or promote inferred/proposed truth to
authoritative truth.

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
