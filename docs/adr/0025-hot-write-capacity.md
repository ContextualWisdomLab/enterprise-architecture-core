# ADR 0025: Prepare append-only write paths for hot partitioning

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Evidence, inbound receipts, transactional outbox events, and transformation
history are append-oriented tables. They are the first database boundaries
that can become hot when one tenant or one event stream dominates writes. A
single unbounded tenant-first index does not provide an explicit routing
contract for a later partition cutover.

## Decision

Migration `0050_hot_write_capacity.sql` adds the same deterministic
`architecture_core.hot_partition_bucket(uuid)` function to every high-write
boundary. It maps the MD5 digest of a tenant UUID to one of 16 stable buckets
without exposing tenant identity or requiring application-side routing. The
digest-based mapping keeps the routing contract reproducible across PostgreSQL
major-version changes. Each boundary also receives a tenant-first hot-write
index and `fillfactor = 80` for new-page headroom.

The current release keeps ordinary tables and foreign-key semantics intact.
The bucket is a routing contract and capacity-preparation measure, not a claim
that the service is already physically partitioned. A future operator can
cut over one boundary to HASH/LIST partitions using the same tenant bucket
contract after measuring row volume, queue lag, write amplification, and
per-tenant skew. That cutover must preserve RLS, composite tenant keys,
transactional outbox ordering, and migration rollback evidence.

## Consequence

- Hot-write scans have an explicit tenant and bucket access path today.
- The migration avoids a table rewrite, data copy, or speculative partition
  count in the current release.
- A future partition cutover has a stable 16-bucket compatibility boundary;
  it still requires production measurements and a separate migration review.
- The acceptance SQL proves the function, table storage parameters, and
  indexes on a real PostgreSQL installation.

## References

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
Table partitioning*. https://www.postgresql.org/docs/18/ddl-partitioning.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
CREATE INDEX*. https://www.postgresql.org/docs/18/sql-createindex.html
