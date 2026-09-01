# Enterprise Architecture Core

`enterprise-architecture-core` is the authoritative enterprise architecture and transformation decision plane for the ContextualWisdomLab ecosystem.

It records business capabilities, applications, interfaces, technology components, lifecycle intervals, evidence, portfolio assessments, architecture objectives/initiatives, target-state scenarios, transformations, and transactional events. It is not a data catalog, physical database designer, workflow engine, or runtime graph store.

## What a buyer can decide

The current development stack includes a **Technology Change Impact & Target-State Planner** plus separately authorized approval, scheduling, start, completion, target-state verification, post-verification monitoring, and target-state replanning surfaces. Given a technology version plus explicit real-world and system-recording cutoffs, the planner joins lifecycle risk to affected applications and capabilities, receipt-backed physical-schema/Data-AI evidence, remediation initiative, target scenario, and transformation state. The result carries deterministic actions such as `approve_target_state`, `schedule_transformation`, `monitor_transformation`, `replan_target_state`, and `verify_target_state`.

When the planner returns `approve_target_state`, an authorized human can submit the exact proposed transformation, UUIDv7 decision request, effective time, reason, and evidence reference. EA Core derives the actor from the verified Keyverse identity, appends authoritative transformation history, and emits the privacy-minimized transformation approval outbox event atomically. Exact retries are idempotent; conflicting reuse of a decision request fails closed.

After approval, a separately authorized scheduler can bind that transformation to one existing authoritative milestone of the same remediation initiative. The milestone remains the source of target-date truth; EA Core records only the governed schedule binding, business/system time, verified actor/reason/evidence, and the privacy-minimized `org.contextualwisdomlab.ea.transformation.scheduled.v1` transactional outbox event. Scheduling does not invent project/task execution state.

A separately authorized operator can then start the scheduled transformation and later record completion. Completion is deliberately non-final: an authorized verifier must record whether the approved target state was actually achieved. A `verified` outcome advances the buyer to `monitor_target_state`; a `gap_detected` outcome advances to `replan_target_state`. Each mutation derives the actor from Keyverse, requires explicit evidence and reason, appends immutable authoritative history, and emits its transactional outbox event atomically. The event payloads do not export the decision actor or reason.

After a verified outcome, a separately authorized monitoring read evaluates the exact bitemporal verification evidence against a bounded freshness policy. `current` directs the buyer to `continue_monitoring`, `stale` to `collect_new_target_state_evidence`, and `gap_detected` to `replan_target_state`. Monitoring itself is read-only. When evidence is stale, the buyer collects newer evidence and submits another human-authorized verification decision; EA Core appends a later `verified` or `gap_detected` observation without reopening execution or rewriting prior history. A detected gap remains terminal for that transformation and requires replanning. Inferred, proposed, stale, or foreign evidence never becomes authoritative success merely by being observed.

When a terminal transformation has `gap_detected`, a separately authorized replanner can create one new governed replacement transformation. The predecessor is not reopened or rewritten: EA Core links the replacement to the terminal predecessor, supersedes the predecessor, creates the replacement in `proposed`, records immutable replan evidence, and emits `org.contextualwisdomlab.ea.transformation.replanned.v1` in the same transaction. Exact retries return the same receipt; conflicting reuse, cross-tenant references, a non-gap predecessor, an already-superseded predecessor, or reuse of a replacement identifier fails closed. The buyer's next action is `approve_target_state`, so the replacement re-enters the same human-governed lifecycle rather than becoming a parallel workflow engine.

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
    ?valid_at=<CWL timestamp>
    &recorded_at=<CWL timestamp>
    &planning_horizon_days=<1..3650>
```

The governed approval endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/approval
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "effective_at": "<CWL timestamp>",
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
  "effective_at": "<CWL timestamp>",
  "decision_reason_text": "<human scheduling reason>",
  "evidence_record_id": "<UUIDv7>"
}
```

The governed start endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/start
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "effective_at": "<CWL timestamp>",
  "decision_reason_text": "<human start reason>",
  "evidence_record_id": "<UUIDv7>"
}
```

The governed completion endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/complete
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "effective_at": "<CWL timestamp>",
  "decision_reason_text": "<human completion reason>",
  "evidence_record_id": "<UUIDv7>"
}
```

The governed target-state verification endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/verification
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "effective_at": "<CWL timestamp>",
  "decision_reason_text": "<human verification reason>",
  "evidence_record_id": "<UUIDv7>",
  "verification_outcome_code": "verified"
}
```

Use `verification_outcome_code: "verified"` only when the evidence demonstrates the approved target state was achieved. Use `"gap_detected"` when evidence shows a material target-state gap; the receipt then directs the operator to replan rather than silently declaring success. After an earlier `verified` result, the same endpoint accepts a later evidence-backed human decision so stale monitoring evidence can be refreshed append-only; it never rewrites prior verification history or reopens execution.

The post-verification monitoring endpoint is:

```text
GET /v1/architecture-transformations/{architecture_transformation_id}/monitoring
    ?valid_at=<CWL timestamp>
    &recorded_at=<CWL timestamp>
    &max_evidence_age_days=<1..3650>
```

The default evidence-age policy is 90 days when `max_evidence_age_days` is omitted. The response binds the returned evidence UUID, verification valid/system times, evidence age, monitoring state, and next action to the requested transformation.

The governed target-state replanning endpoint is:

```text
POST /v1/architecture-transformations/{architecture_transformation_id}/replan
Content-Type: application/json

{
  "decision_request_id": "<UUIDv7>",
  "replacement_architecture_transformation_id": "<UUIDv7>",
  "architecture_scenario_id": "<UUIDv7>",
  "remediation_initiative_id": "<UUIDv7>",
  "transformation_code": "database_target_state_v2",
  "transformation_title": "Replace the gap-detected target state",
  "transformation_description": "Describe the bounded replacement target state.",
  "effective_at": "<CWL timestamp>",
  "decision_reason_text": "<human replanning reason>",
  "evidence_record_id": "<UUIDv7>"
}
```

The path UUID identifies the terminal predecessor; the body must identify a distinct replacement. A fresh receipt returns `next_action: "approve_target_state"`; an exact idempotent replay returns the same immutable replan evidence with `replayed: true`.

All governed surfaces require a Keyverse RS256 bearer. Configure `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, `EA_OIDC_JWKS_URL`, `EA_TENANT_CLAIM`, `EA_ROLE_CLAIM`, and `EA_READ_ROLES`. Configure `EA_APPROVAL_ROLES`, `EA_SCHEDULE_ROLES`, `EA_START_ROLES`, `EA_COMPLETE_ROLES`, `EA_VERIFY_ROLES`, `EA_MONITOR_ROLES`, and `EA_REPLAN_ROLES` separately for their purpose-bound mutation or monitoring boundaries. Signature, issuer, audience, expiration, tenant UUID, and the operation-specific role are verified before database access. JWKS retrieval is same-origin, redirect-denied, bounded, and fail-closed.

The `ea_runtime` login has no direct application-table authority. It receives only purpose-bound PostgreSQL functions after service-side verification, including `read_technology_target_state_plan(...)`, `approve_target_state(...)`, `schedule_transformation(...)`, `start_scheduled_transformation(...)`, `complete_started_transformation(...)`, `record_target_state_verification(...)`, `read_target_state_monitoring_status(...)`, and `record_target_state_replan(...)`. Callers cannot supply a decision actor, and no surface grants direct access to foreign product stores.

## Validation

```bash
uv sync --extra dev --locked
uv run --extra dev python -m coverage run -m pytest -q
uv run --extra dev python -m coverage report
uv run --extra dev python scripts/validate_repository.py
```

CI additionally rehearses clean install/upgrade/rollback on real PostgreSQL, runtime-role isolation, the planner and full governed transformation lifecycle, post-verification monitoring and replanning, OpenAPI/AsyncAPI contracts, installed-package smoke, Python 3.11–3.14, exact 100% owned production statement/branch coverage, and exact-head package/SBOM evidence.
