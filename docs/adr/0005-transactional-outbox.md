# ADR 0005: Publish committed changes through a transactional outbox

- **Status:** Accepted
- **Date:** 2026-08-16

## Decision

Domain writes and outbox events occur in one PostgreSQL transaction. Publishers
retry independently and consumers deduplicate by source plus event identifier.

## Consequence

A projection outage cannot lose authoritative changes or force dual writes.
