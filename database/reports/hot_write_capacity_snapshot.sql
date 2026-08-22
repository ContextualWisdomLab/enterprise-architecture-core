\if :ON_ERROR_STOP
\set cwl_capacity_previous_on_error_stop on
\else
\set cwl_capacity_previous_on_error_stop off
\endif
\set ON_ERROR_STOP on

\if :{?tenant_id}
\else
\echo 'tenant_id is required: psql --set tenant_id=<uuid> --file database/reports/hot_write_capacity_snapshot.sql'
DO $$
BEGIN
    RAISE EXCEPTION 'tenant_id is required';
END;
$$;
\endif

-- Preserve the caller's tenant context so an operator can include this report in
-- a longer psql session without changing the authorization context of later SQL.
SELECT pg_catalog.current_setting('app.tenant_record_id', true)
    AS cwl_capacity_previous_tenant_record_id \gset

\set cwl_capacity_report_failed false
\set ON_ERROR_STOP off

-- The explicit tenant predicate remains in every branch even for owner
-- connections, so this report does not accidentally become cross-tenant.
-- Run it through an approved operator/owner connection; no runtime grant is
-- installed for this direct read-only report.
SELECT pg_catalog.set_config(
    'app.tenant_record_id',
    :'tenant_id',
    false
) AS cwl_capacity_installed_tenant_record_id \gset

\if :ERROR
\set cwl_capacity_report_failed true
\endif

WITH snapshot AS (
    SELECT
        clock_timestamp() AS snapshot_at,
        :'tenant_id'::uuid AS tenant_record_id,
        architecture_core.hot_partition_bucket(:'tenant_id'::uuid)
            AS hot_partition_bucket,
        pg_catalog.pg_stat_wal.wal_bytes
    FROM pg_catalog.pg_stat_wal
), boundary_metrics AS (
    SELECT
        'evidence_record'::text AS boundary_name,
        count(*)::bigint AS row_count,
        min(recorded_at) AS oldest_write_at,
        max(recorded_at) AS newest_write_at,
        NULL::bigint AS active_work_count,
        NULL::timestamptz AS oldest_active_at
    FROM architecture_core.evidence_record
    WHERE tenant_record_id = :'tenant_id'::uuid
    UNION ALL
    SELECT
        'outbox_event',
        count(*)::bigint,
        min(recorded_at),
        max(recorded_at),
        count(*) FILTER (
            WHERE publish_status_code IN ('pending', 'publishing', 'failed')
        )::bigint,
        min(recorded_at) FILTER (
            WHERE publish_status_code IN ('pending', 'publishing', 'failed')
        )
    FROM architecture_core.outbox_event
    WHERE tenant_record_id = :'tenant_id'::uuid
    UNION ALL
    SELECT
        'projection_receipt',
        count(*)::bigint,
        min(received_at),
        max(received_at),
        count(*) FILTER (
            WHERE processing_status_code IN ('received', 'processing')
        )::bigint,
        min(received_at) FILTER (
            WHERE processing_status_code IN ('received', 'processing')
        )
    FROM architecture_core.projection_receipt
    WHERE tenant_record_id = :'tenant_id'::uuid
    UNION ALL
    SELECT
        'transformation_history_record',
        count(*)::bigint,
        min(recorded_at),
        max(recorded_at),
        NULL::bigint,
        NULL::timestamptz
    FROM architecture_core.transformation_history_record
    WHERE tenant_record_id = :'tenant_id'::uuid
)
SELECT
    snapshot.snapshot_at,
    snapshot.tenant_record_id,
    boundary_metrics.boundary_name,
    snapshot.hot_partition_bucket,
    boundary_metrics.row_count,
    boundary_metrics.oldest_write_at,
    boundary_metrics.newest_write_at,
    boundary_metrics.active_work_count,
    boundary_metrics.oldest_active_at,
    CASE
        WHEN boundary_metrics.oldest_active_at IS NULL THEN NULL::numeric
        ELSE extract(
            epoch FROM snapshot.snapshot_at - boundary_metrics.oldest_active_at
        )
    END AS queue_lag_seconds,
    pg_catalog.pg_total_relation_size(
        format('%I.%I', 'architecture_core', boundary_metrics.boundary_name)
            ::regclass
    ) AS table_size_bytes,
    pg_catalog.pg_indexes_size(
        format('%I.%I', 'architecture_core', boundary_metrics.boundary_name)
            ::regclass
    ) AS index_size_bytes,
    table_stats.n_tup_ins,
    table_stats.n_tup_upd,
    table_stats.n_tup_del,
    snapshot.wal_bytes
FROM snapshot
JOIN boundary_metrics ON true
JOIN pg_catalog.pg_stat_user_tables AS table_stats
  ON table_stats.schemaname = 'architecture_core'
 AND table_stats.relname = boundary_metrics.boundary_name
ORDER BY boundary_metrics.boundary_name;

\if :ERROR
\set cwl_capacity_report_failed true
\endif

\if :{?cwl_capacity_previous_tenant_record_id}
SELECT pg_catalog.set_config(
    'app.tenant_record_id',
    :'cwl_capacity_previous_tenant_record_id',
    false
) AS cwl_capacity_restored_tenant_record_id \gset
\else
RESET app.tenant_record_id;
\endif

\if :ERROR
\set cwl_capacity_report_failed true
\endif

-- A report failure must still abort after tenant context has been restored.
\set ON_ERROR_STOP on
\if :cwl_capacity_report_failed
\echo 'hot-write capacity snapshot failed after restoring caller tenant context'
SELECT 1 / 0;
\endif

-- Successful inclusion is side-effect-free with respect to the caller's psql
-- error policy, including sessions that intentionally keep ON_ERROR_STOP off.
\if :cwl_capacity_previous_on_error_stop
\set ON_ERROR_STOP on
\else
\set ON_ERROR_STOP off
\endif

\unset cwl_capacity_previous_tenant_record_id
\unset cwl_capacity_installed_tenant_record_id
\unset cwl_capacity_restored_tenant_record_id
\unset cwl_capacity_report_failed
\unset cwl_capacity_previous_on_error_stop
