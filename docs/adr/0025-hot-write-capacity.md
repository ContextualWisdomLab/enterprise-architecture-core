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

The read-only `database/reports/hot_write_capacity_snapshot.sql` query provides
the repeatable baseline for that measurement. It requires one `tenant_id`,
reports exact row volume and write-time range for each boundary, pending or
active queue lag where applicable, the derived bucket, relation/index sizes,
relation-wide cumulative tuple counters, and the cluster-wide cumulative WAL
counter from PostgreSQL `pg_stat_wal`. Operators compare tenant-scoped metrics
between snapshots for the same tenant and interval. Relation tuple counters
remain relation-wide, while `pg_stat_wal` is one cluster-wide row; neither is a
tenant-isolated metric and neither may be attributed to the selected tenant.
The counters are not a production capacity claim. Negative queue-lag values
indicate fixture or clock data that is in the future relative to the snapshot
and require investigation rather than clamping.

## Consequence

- Hot-write scans have an explicit tenant and bucket access path today.
- The migration avoids a table rewrite, data copy, or speculative partition
  count in the current release.
- A future partition cutover has a stable 16-bucket compatibility boundary;
  it still requires production measurements and a separate migration review.
- The acceptance SQL proves the function, table storage parameters, and
  indexes on a real PostgreSQL installation.
- The snapshot query makes the required measurement inputs reproducible without
  adding a cross-tenant database object or changing the write path.

## References

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
Table partitioning*. https://www.postgresql.org/docs/18/ddl-partitioning.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
CREATE INDEX*. https://www.postgresql.org/docs/18/sql-createindex.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation:
The cumulative statistics system*. https://www.postgresql.org/docs/18/monitoring-stats.html
