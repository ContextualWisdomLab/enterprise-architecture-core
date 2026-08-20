BEGIN;

-- PostgreSQL 18 returns NULL from uuid_extract_version() for UUIDs outside the
-- RFC 9562 variant. SQL CHECK constraints accept UNKNOWN, so the historical
-- `uuid_extract_version(value) = 7` form is not fail-closed for those UUIDs.
-- Harden every existing architecture_core UUID-version CHECK in place rather
-- than fixing only the newest reassessment table and leaving older canonical
-- identifiers vulnerable to the same three-valued-logic bypass.
DO $$
DECLARE
  constraint_record record;
  hardened_definition text;
BEGIN
  FOR constraint_record IN
    SELECT
        namespace_record.nspname AS schema_name,
        table_record.relname AS table_name,
        constraint_catalog.conname AS constraint_name,
        pg_get_constraintdef(constraint_catalog.oid) AS constraint_definition
      FROM pg_constraint AS constraint_catalog
      JOIN pg_class AS table_record
        ON table_record.oid = constraint_catalog.conrelid
      JOIN pg_namespace AS namespace_record
        ON namespace_record.oid = table_record.relnamespace
     WHERE namespace_record.nspname = 'architecture_core'
       AND constraint_catalog.contype = 'c'
       AND pg_get_constraintdef(constraint_catalog.oid) LIKE
           '%uuid_extract_version%'
       AND pg_get_constraintdef(constraint_catalog.oid) NOT LIKE
           '%IS NOT DISTINCT FROM 7%'
     ORDER BY table_record.relname, constraint_catalog.conname
  LOOP
    hardened_definition := regexp_replace(
      constraint_record.constraint_definition,
      E'(uuid_extract_version\\([^)]*\\)) = 7',
      E'\\1 IS NOT DISTINCT FROM 7',
      'g'
    );

    IF hardened_definition IS NOT DISTINCT FROM
       constraint_record.constraint_definition THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = format(
          'unable to harden UUIDv7 constraint %I.%I.%I',
          constraint_record.schema_name,
          constraint_record.table_name,
          constraint_record.constraint_name
        );
    END IF;

    EXECUTE format(
      'ALTER TABLE %I.%I DROP CONSTRAINT %I',
      constraint_record.schema_name,
      constraint_record.table_name,
      constraint_record.constraint_name
    );
    EXECUTE format(
      'ALTER TABLE %I.%I ADD CONSTRAINT %I %s',
      constraint_record.schema_name,
      constraint_record.table_name,
      constraint_record.constraint_name,
      hardened_definition
    );
  END LOOP;
END;
$$;

COMMIT;
