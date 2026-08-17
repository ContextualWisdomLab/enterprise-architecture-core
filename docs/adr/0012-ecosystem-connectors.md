# ADR 0012: Connect Neighbor Systems Through Contracts, Not SQL

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

The highest-leverage owned neighbors are Keyverse, context-graph-contracts,
semantic-data-portal, pg-erd-cloud, LineageWeave, naruon, and the organization
`.github` governance repository. Each exchange is recorded in
`contracts/connectors/ecosystem.json` as an OpenAPI, AsyncAPI/CloudEvents, or
canonical-reference connector. Direct cross-service SQL is prohibited.

Inferred LineageWeave relations and observed pg-erd-cloud evidence enter as
non-authoritative truth until a reviewed command accepts them.

## Consequence

The service can be deployed alone. When imported as a module in the CWL
ecosystem, it still owns only architecture and transformation facts and points
operators at the next configuration action for each neighbor.
