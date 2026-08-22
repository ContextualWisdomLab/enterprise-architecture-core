\set ON_ERROR_STOP on
\set tenant_id '0195d145-64e8-7f4f-8a23-a0cc784cb711'

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb799',
    false
);

\ir ../reports/hot_write_capacity_snapshot.sql

DO $$
BEGIN
    IF pg_catalog.current_setting('app.tenant_record_id', true)
       IS DISTINCT FROM '0195d145-64e8-7f4f-8a23-a0cc784cb799' THEN
        RAISE EXCEPTION
          'hot-write snapshot leaked its tenant context into the caller session';
    END IF;

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

RESET app.tenant_record_id;
\ir ../reports/hot_write_capacity_snapshot.sql

DO $$
BEGIN
    IF pg_catalog.current_setting('app.tenant_record_id', true) IS DISTINCT FROM '' THEN
        RAISE EXCEPTION
          'hot-write snapshot changed an unset caller tenant context';
    END IF;
END;
$$;

SELECT 'hot-write-capacity-snapshot-unset-context-ok' AS verification;

-- A report included in a longer psql operator session must preserve the caller's
-- error policy just as it preserves tenant authorization context. The report
-- temporarily relaxes ON_ERROR_STOP so it can restore context before surfacing
-- a report failure, but a successful include must not force the caller to `on`.
\set ON_ERROR_STOP off
\ir ../reports/hot_write_capacity_snapshot.sql
\if :ON_ERROR_STOP
\echo 'hot-write snapshot changed caller ON_ERROR_STOP policy'
SELECT 1 / 0;
\endif
\set ON_ERROR_STOP on

SELECT 'hot-write-capacity-snapshot-error-policy-ok' AS verification;
