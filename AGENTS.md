# Agent Development Rules

## Product boundary

- This repository owns enterprise architecture and transformation facts.
- It does not own datasets, columns, data quality, physical database snapshots,
  inferred narrative lineage, credentials, or project execution truth.
- Services exchange OpenAPI, AsyncAPI/CloudEvents, and canonical references;
  direct cross-service SQL is prohibited. Neighbor exchanges are listed in
  `contracts/connectors/ecosystem.json`.
- The process surface is `GET /health` then `GET /ready` on `0.0.0.0:$PORT`.
  Domain commands stay unpublished until Keyverse claims are bound.

## Data model

- All database objects use at least two lower-snake words.
- The canonical write model is third normal form; graph structures are derived
  read models.
- Valid time and system-recording time remain distinct.
- Historical records are closed or superseded, never silently overwritten.
- Cross-tenant references must be blocked by composite foreign keys and policy.

## AI and evidence

- LLM or inferred proposals never become authoritative without an explicit
  reviewed command.
- Every assessment and material relationship requires evidence or a documented
  omission reason.
- Credentials, DSNs, tokens, and raw personal data must not enter architecture
  events or evidence summaries.

## Quality

- Production code requires 100% statement and branch coverage and public API
  docstrings.
- Migrations require clean-install and upgrade tests against real PostgreSQL.
- API and event contracts require positive and negative conformance fixtures.
