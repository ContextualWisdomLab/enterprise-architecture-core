\set ON_ERROR_STOP on
\set tenant_id '0195d145-64e8-7f4f-8a23-a0cc784cb711'

-- A fresh psql session starts without a caller tenant GUC. Exercise the report's
-- true RESET path before any test installs a placeholder value in this session.
\ir ../reports/hot_write_capacity_snapshot.sql

DO $$
BEGIN
    IF COALESCE(
        NULLIF(pg_catalog.current_setting('app.tenant_record_id', true), ''),
        '<unset>'
    ) IS DISTINCT FROM '<unset>' THEN
        RAISE EXCEPTION
          'hot-write snapshot left its tenant context installed after standalone use';
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

SELECT 'hot-write-capacity-snapshot-unset-context-ok' AS verification;

-- A pre-existing tenant context must round-trip exactly through an included
-- report rather than being cleared or replaced by the requested report tenant.
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
END;
$$;

SELECT 'hot-write-capacity-snapshot-existing-context-ok' AS verification;

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

-- Missing input is a standalone process boundary because ON_ERROR_STOP must
-- terminate that psql invocation. SHELL_ERROR is a PostgreSQL 18 psql special
-- variable and lets this parent acceptance script assert the child failed.
\! rm -f /tmp/cwl-capacity-missing-tenant.log
\! psql --host 127.0.0.1 --username ea_app --dbname ea_core --set ON_ERROR_STOP=1 --file database/reports/hot_write_capacity_snapshot.sql >/tmp/cwl-capacity-missing-tenant.log 2>&1
\if :SHELL_ERROR
\else
\echo 'hot-write snapshot accepted a missing tenant_id'
SELECT 1 / 0;
\endif
\! grep --fixed-strings 'tenant_id is required: psql --set tenant_id=<uuid>' /tmp/cwl-capacity-missing-tenant.log
\if :SHELL_ERROR
\echo 'missing-tenant failure did not emit the operator diagnostic'
SELECT 1 / 0;
\endif

-- An invalid tenant reaches the report body, fails the UUID cast, restores the
-- caller context, and then deliberately re-raises failure. This executes the
-- fail-after-restoration branch rather than merely checking its source text.
\! rm -f /tmp/cwl-capacity-invalid-tenant.log
\! psql --host 127.0.0.1 --username ea_app --dbname ea_core --set ON_ERROR_STOP=1 --set tenant_id=not-a-uuid --file database/reports/hot_write_capacity_snapshot.sql >/tmp/cwl-capacity-invalid-tenant.log 2>&1
\if :SHELL_ERROR
\else
\echo 'hot-write snapshot accepted an invalid tenant as successful'
SELECT 1 / 0;
\endif
\! grep --fixed-strings 'hot-write capacity snapshot failed after restoring caller tenant context' /tmp/cwl-capacity-invalid-tenant.log
\if :SHELL_ERROR
\echo 'failed snapshot did not emit the post-restoration diagnostic'
SELECT 1 / 0;
\endif
\! rm -f /tmp/cwl-capacity-missing-tenant.log /tmp/cwl-capacity-invalid-tenant.log

SELECT 'hot-write-capacity-snapshot-failure-boundaries-ok' AS verification;
