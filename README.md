# Enterprise Architecture Core

`enterprise-architecture-core` is the authoritative enterprise architecture and transformation decision plane for the ContextualWisdomLab ecosystem.

It records business capabilities, applications, interfaces, technology components, lifecycle intervals, evidence, portfolio assessments, architecture objectives/initiatives, target-state scenarios, transformations, and transactional events. It is not a data catalog, physical database designer, workflow engine, or runtime graph store.

## What a buyer can decide

The current development stack includes a **Technology Change Impact & Target-State Planner** plus separately authorized approval and scheduling commands. Given a technology version plus explicit real-world and system-recording cutoffs, the planner joins lifecycle risk to affected applications and capabilities, receipt-backed physical-schema/Data-AI evidence, remediation initiative, target scenario, and transformation state. The result carries deterministic actions such as `approve_target_state`, `schedule_transformation`, `monitor_transformation`, `replan_target_state`, and `verify_target_state`.

When the planner returns `approve_target_state`, an authorized human can submit the exact proposed transformation, UUIDv7 decision request, effective time, reason, and evidence reference. EA Core derives the actor from the verified Keyverse identity, appends authoritative transformation history, and emits the privacy-minimized transformation approval outbox event atomically. Exact retries are idempotent; conflicting reuse of a decision request fails closed.

After approval, a separately authorized scheduler can bind that transformation to one existing authoritative milestone of the same remediation initiative. The milestone remains the source of target-date truth; EA Core records only the governed schedule binding, business/system time, verified actor/reason/evidence, and the privacy-minimized `org.contextualwisdomlab.ea.transformation.scheduled.v1` transactional outbox event. Scheduling does not invent project/task execution state.

`semantic-data-portal` remains the Data/AI Context system of record; `pg-erd-cloud` remains physical schema/design evidence; LineageWeave evidence remains inferred/proposed unless governed elsewhere. EA Core stores canonical references and receipt evidence rather than copying those products or querying their application tables.

## Authority and time

The canonical write model is normalized PostgreSQL with UUIDv7 identity, canonical reference checks, typed relations, separate valid/system time, non-overlapping active intervals, tenant isolation, truth-origin/provenance guards, and transactional outbox evidence. Inferred/proposed evidence cannot silently become authoritative.

Target-state scenarios use immutable baselines plus ordered append-preserving object/relation deltas. `project_scenario_objects(uuid)` and `project_scenario_relations(uuid)` reconstruct target state without mutating authoritative facts. Requested-present relations whose projected source or target is absent remain auditable but cannot appear active.

## Run the process and decision surface

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

The governed approval endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/approval
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "effective_at": "<CWL leap-second-free timestamp>",
  "decision_reason_text": "<human decision reason>",
  "evidence_record_id": "<UUIDv7>"
}
```

The governed scheduling endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/schedule
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "initiative_milestone_id": "<UUIDv7>",
  "effective_at": "<CWL leap-second-free timestamp>",
  "decision_reason_text": "<human scheduling reason>",
  "evidence_record_id": "<UUIDv7>"
}
```

Both governed POST commands reject `Transfer-Encoding`, require exactly one bounded `Content-Length`, and parse only strict UTF-8 `application/json` without duplicate member names.

All three surfaces require a Keyverse RS256 bearer. Configure `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, `EA_ROLE_CLAIM`, and `EA_READ_ROLES`; configure `EA_APPROVAL_ROLES` and `EA_SCHEDULE_ROLES` separately for their mutation boundaries. Signature, issuer, audience, expiration, tenant UUID, and the operation-specific role are verified before database access. JWKS retrieval is same-origin, redirect-denied, bounded, and fail-closed.

The `ea_runtime` login has no direct application-table authority. It receives only the purpose-bound `read_technology_target_state_plan(...)`, `approve_target_state(...)`, and `schedule_transformation(...)` wrappers after service-side verification. Callers cannot supply a decision actor, and no surface grants direct access to foreign product stores.

## Validation

```bash
uv sync --extra dev --locked
uv run --extra dev python -m coverage run -m pytest -q
uv run --extra dev python -m coverage report
uv run --extra dev python scripts/validate_repository.py
```

CI additionally rehearses clean install/upgrade/rollback on real PostgreSQL, runtime-role isolation, planner/approval/scheduling behavior, OpenAPI/AsyncAPI contracts, installed-package smoke, Python 3.11–3.14, exact 100% owned production statement/branch coverage, and exact-head package/SBOM evidence.
