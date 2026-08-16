# ADR 0002: Use a normalized relational write model

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

PostgreSQL third-normal-form tables are authoritative. Graph, search, and
portfolio views are derived projections.

## Consequence

Business constraints, temporal history, and transactional updates remain
explicit while graph projections can be rebuilt.
