# Enterprise Architecture Core

`enterprise-architecture-core` is the authoritative enterprise architecture and transformation decision plane for the ContextualWisdomLab ecosystem.

It records business capabilities, applications, interfaces, technology components, lifecycle intervals, evidence, portfolio assessments, architecture objectives/initiatives, target-state scenarios, transformations, and transactional events. It is not a data catalog, physical database designer, workflow engine, or runtime graph store.

## What a buyer can decide

The current development stack includes a read-only **Technology Change Impact & Target-State Planner**. Given a technology version plus explicit real-world and system-recording cutoffs, it joins lifecycle risk to affected applications and capabilities, receipt-backed physical-schema/Data-AI evidence, remediation initiative, target scenario, and transformation state. The result carries deterministic actions such as `approve_target_state`, `schedule_transformation`, `monitor_transformation`, `replan_target_state`, and `verify_target_state`.

`semantic-data-portal` remains the Data/AI Context system of record; `pg-erd-cloud` remains physical schema/design evidence; LineageWeave evidence remains inferred/proposed unless governed elsewhere. EA Core stores canonical references and receipt evidence rather than copying those products or querying their application tables.

## Authority and time

The canonical write model is normalized PostgreSQL with UUIDv7 identity, canonical reference checks, typed relations, separate valid/system time, non-overlapping active intervals, tenant isolation, truth-origin/provenance guards, and transactional outbox evidence. Inferred/proposed evidence cannot silently become authoritative.

Target-state scenarios use immutable baselines plus ordered append-preserving object/relation deltas. `project_scenario_objects(uuid)` and `project_scenario_relations(uuid)` reconstruct target state without mutating authoritative facts. Requested-present relations whose projected source or target is absent remain auditable but cannot appear active.

## Run the process and planner

```bash
uv sync --extra dev --locked
uv run --extra dev ea-core
```

The process binds `0.0.0.0:$PORT`. Call `GET /health`, then `GET /ready`; a 503 means repair the false dependency before serving tenant traffic.

The planner endpoint is:

```text
GET /v1/technology-target-state-plans/{technology_version_id}
    ?valid_at=<CWL leap-second-free timestamp>
    &recorded_at=<CWL leap-second-free timestamp>
    &planning_horizon_days=<1..3650>
```

It requires a Keyverse RS256 bearer. Configure `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, `EA_ROLE_CLAIM`, and `EA_READ_ROLES`. Signature, issuer, audience, expiration, tenant UUID, and read role are verified before database access. JWKS retrieval is same-origin, redirect-denied, bounded, and fail-closed.

The `ea_runtime` login has no direct application-table or underlying-projector authority. It receives only the purpose-bound `read_technology_target_state_plan(...)` function after service-side verification. This is a read surface, not a command or authorization framework for future mutations.

## Validation

```bash
uv sync --extra dev --locked
uv run --extra dev python -m coverage run -m pytest -q
uv run --extra dev python -m coverage report
uv run --extra dev python scripts/validate_repository.py
```

CI additionally rehearses clean install/upgrade/rollback on real PostgreSQL, runtime-role isolation, installed-package smoke, Python 3.11–3.14, exact 100% owned production statement/branch coverage, and exact-head package/SBOM evidence.
