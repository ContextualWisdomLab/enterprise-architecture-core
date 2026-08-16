# Product Requirements Document

## Product definition

Enterprise Architecture Core is the authoritative decision plane for business
capabilities, applications, interfaces, technology components, lifecycle,
portfolio assessments, and target-state transformations within the CWL
ecosystem.

## Buyer problem

Organizations often maintain data lineage, repository metadata, application
inventories, and technology lifecycle information in disconnected tools. They
cannot reliably answer which business capability, application, data product,
or AI agent is affected when a technology becomes unsupported or an
application is replaced.

## Primary users

- Enterprise architects maintaining current and target architecture.
- Product and platform owners reviewing application fit and technology risk.
- Transformation leads comparing migration scenarios.
- Security and compliance reviewers tracing evidence and accountability.

## P0 outcomes

1. Record capability, application, interface, and technology inventories.
2. Preserve bitemporal object, lifecycle, and relationship history.
3. Attach every material assertion to evidence or an omission decision.
4. Publish committed changes through a transactional CloudEvents outbox.
5. Authenticate users through Keyverse OIDC without storing credentials.
6. Provide provider-neutral OpenAPI and AsyncAPI contracts.
7. Keep the relational write model in third normal form.
8. Keep data/AI context and physical database evidence in their owning systems.

## P0 exclusions

- Arbitrary meta-model editing.
- Current/target graph visualization UI.
- Runtime CRUD implementation.
- Atlan or SAP LeanIX proprietary adapters.
- Automatic promotion of LLM or inferred findings.
- Project execution tracking or employee records.

## Acceptance criteria

- Accepted architecture decisions are internally consistent.
- The initial migration passes naming, temporal, outbox, and 3NF review gates.
- OpenAPI identifies Keyverse verification requirements and the implemented
  health/ready process surface.
- AsyncAPI publishes object and lifecycle change contracts.
- The connector catalog names Keyverse, Context Graph, Semantic Data Portal,
  pg-erd-cloud, LineageWeave, naruon, and organization governance exchanges.
- Repository validation and all tests pass at 100% statement/branch coverage.
