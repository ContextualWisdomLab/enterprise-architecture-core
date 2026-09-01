# Enterprise Architecture Core

**The authoritative enterprise-architecture decision plane for ContextualWisdomLab.**

Enterprise Architecture Core connects business capabilities, applications, interfaces, technologies, lifecycle evidence, portfolio assessments, and target-state transformations so an organization can answer a practical question: **what is affected, what should change, and what evidence supports that decision?**

It is built for enterprise architects, product and platform owners, transformation leads, and security/compliance reviewers who need current-state and target-state decisions to remain traceable over both business time and system-recorded time.

> This README describes the current candidate branch. Protected integration history remains shipped authority until this branch and its dependency stack pass current governance and merge.

## Why it exists

Architecture evidence is usually fragmented across repositories, catalogs, schema tools, lifecycle feeds, plans, and operational systems. That makes cross-product change questions expensive and error-prone: a technology reaches end of support, but no single decision surface can reliably connect it to affected applications, capabilities, evidence gaps, remediation work, and target-state verification.

Enterprise Architecture Core provides a governed decision plane without turning itself into every adjacent system of record.

| Need | What Enterprise Architecture Core provides |
| --- | --- |
| Architecture inventory | Business capability, application, interface, technology, lifecycle, and relationship records |
| Time-aware truth | Separate valid/effective time and system-recorded time with evidence and truth origin |
| Portfolio decisions | Evidence-preserving assessment reads and summaries without mixing incompatible scales |
| Change impact | Technology-risk and affected-architecture projections for target-state planning |
| Transformation governance | Human-authorized approval, scheduling, execution-state evidence, verification, monitoring, and replanning |
| Data/AI improvement | Evidence-gap and reassessment loops that keep the source catalog authoritative |
| Integration | Explicit contracts and references instead of cross-service application-table reads |
| Auditability | Immutable history plus privacy-minimized transactional events for material changes |

## Product boundary

Enterprise Architecture Core owns enterprise-architecture **decision truth**. It does not replace the products that produce specialized evidence or execute unrelated workflows.

```text
Specialist evidence owners
        │
        │ released contracts / governed references
        ▼
┌──────────────────────────────────────┐
│       Enterprise Architecture Core   │
│                                      │
│ inventory · assessment · target      │
│ state · transformation decisions     │
└──────────────────┬───────────────────┘
                   │
          governed decisions / events
                   │
                   ▼
      product and platform consumers
```

Key boundaries remain explicit:

- **Semantic Data Portal** owns Data/AI Context source assessments and semantic catalog truth.
- **pg-erd-cloud** owns physical schema/design evidence.
- **LineageWeave** provides inferred lineage evidence; inference does not become authoritative EA truth automatically.
- **Context Graph Contracts** owns shared interoperability contracts when an immutable released contract exists.
- **Keyverse** owns identity and OIDC authority.
- Product-specific runtime state, employee records, project/task execution, and arbitrary workflow orchestration remain outside this repository.

## What you can do

### Assess architecture and technology risk

Maintain architecture inventory and lifecycle evidence, inspect tenant-scoped portfolio facts, and connect technology risk to affected applications and business capabilities without flattening evidence provenance.

### Plan and govern target-state change

Build target-state scenarios from immutable baselines plus ordered deltas, evaluate change impact, and move a transformation through separately authorized decisions. Verification is evidence-backed and append-only; a detected gap leads to governed replanning rather than silently rewriting the prior outcome.

### Close evidence gaps without stealing source authority

Project external assessment evidence through explicit contracts, create accountable EA-side remediation work, and request reassessment only when the evidence boundary permits it. The source product remains authoritative for its own assessment result.

## Quickstart

The current package is `enterprise-architecture-core` `0.1.0`, requires Python 3.11+, and uses a locked `uv` development environment.

```bash
uv sync --extra dev --locked
uv run --extra dev ea-core
```

The process binds to `0.0.0.0:$PORT`. Use liveness and readiness separately:

```bash
curl -sS http://127.0.0.1:${PORT:-8000}/health
curl -sS http://127.0.0.1:${PORT:-8000}/ready
```

`/health` proves the process is alive. A `503` from `/ready` means a required dependency or configuration boundary is not ready and should be repaired before serving tenant traffic.

Production-style decision surfaces require reviewed PostgreSQL and Keyverse OIDC configuration. See [`docs/OPERABILITY.md`](docs/OPERABILITY.md), [`docs/SECURITY.md`](docs/SECURITY.md), and [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) rather than copying environment or database internals from examples.

## API and integration context

The service exposes provider-neutral HTTP contracts for architecture reads and governed decision workflows. The full request/response and authorization contract lives in [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

A representative planning read is:

```text
GET /v1/technology-target-state-plans/{technology_version_id}
    ?valid_at=<CWL timestamp>
    &recorded_at=<CWL timestamp>
    &planning_horizon_days=<1..3650>
```

Mutating workflows require purpose-specific authorization and evidence. Callers do not get database-table authority, cannot supply a trusted decision actor in place of verified identity, and cannot promote inferred or foreign evidence into authoritative architecture truth by assertion.

## Architecture principles

- **Evidence before authority.** Material assertions retain provenance or an explicit omission decision.
- **Bitemporal by design.** Business-effective and system-recorded time are distinct.
- **Human-governed consequential change.** Model/inferred output can inform review but does not self-promote to authoritative decisions.
- **Append, do not rewrite.** Verification, supersession, and replanning preserve prior decision history.
- **3NF write model.** The relational authority model stays normalized rather than becoming an unbounded graph or JSON store.
- **No cross-service table access.** Foreign products are consumed through released contracts, governed references, or adapters.
- **Transactional evidence.** Material writes and their privacy-minimized outbox evidence are committed together.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/CONTEXT_MAP.md`](docs/CONTEXT_MAP.md), and [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) for the detailed design.

## Quality and status

The source tree identifies the package as **0.1.0 / Alpha**. The repository's current quality contract includes Python 3.11–3.14 coverage, strict repository validation, PostgreSQL acceptance/rehearsal, installed-package smoke checks, contract validation, and an exact **100% owned production statement/branch coverage** threshold.

Those are engineering gates, not claims of customer adoption, production scale, certification, or commercial readiness. Operational, security, release, and acquisition evidence remain separate and must be evaluated from their current artifacts.

Run the local validation path with:

```bash
uv sync --extra dev --locked
uv run --extra dev python -m coverage run -m pytest -q
uv run --extra dev python -m coverage report
uv run --extra dev python scripts/validate_repository.py
```

## Documentation map

| Topic | Source |
| --- | --- |
| Product requirements | [`docs/PRD.md`](docs/PRD.md) |
| Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| DDD context map | [`docs/CONTEXT_MAP.md`](docs/CONTEXT_MAP.md) |
| API contract | [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) |
| Data model | [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) |
| Security | [`docs/SECURITY.md`](docs/SECURITY.md) |
| Test strategy | [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md) |
| Operability | [`docs/OPERABILITY.md`](docs/OPERABILITY.md) |
| Product/technical gaps | [`docs/product-technical-gap-baseline.md`](docs/product-technical-gap-baseline.md) |
| Architecture decisions | [`docs/adr/README.md`](docs/adr/README.md) |

## Contributing

Start with the PRD, architecture, context map, and applicable ADR before changing a domain or integration contract. Keep implementation, tests, documentation, and public claims aligned to the same revision.

If a defect belongs to a dedicated product or shared-contract owner, repair it there instead of introducing a local shadow implementation. New dependencies must be commercially usable under the intended distribution model and retain required provenance and attribution.

## License

Enterprise Architecture Core is licensed under the [Apache License 2.0](LICENSE).
