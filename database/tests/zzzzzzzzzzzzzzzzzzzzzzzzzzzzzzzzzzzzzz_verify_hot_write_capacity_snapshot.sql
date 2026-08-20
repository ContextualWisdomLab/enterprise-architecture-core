\set ON_ERROR_STOP on
\set tenant_id '0195d145-64e8-7f4f-8a23-a0cc784cb711'

\ir ../reports/hot_write_capacity_snapshot.sql

DO $$
BEGIN
    IF (
        SELECT count(*)
        FROM pg_catalog.pg_stat_user_tables
        WHERE schemaname = 'architecture_core'
          AND relname IN (
              'evidence_record',
              'outbox_event',
              'projection_receipt',
              'transformation_history_record'
          )
    ) <> 4 THEN
        RAISE EXCEPTION 'hot-write snapshot boundary inventory is incomplete';
    END IF;
END;
$$;

SELECT 'hot-write-capacity-snapshot-ok' AS verification;
