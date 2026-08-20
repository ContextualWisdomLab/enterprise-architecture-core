\set ON_ERROR_STOP on

-- Behavioral UUID variant regressions exercise representative foundation and
-- reassessment writes. This catalog acceptance prevents another table from
-- retaining the same SQL-UNKNOWN form unnoticed.
DO $$
DECLARE
  vulnerable_constraints text;
BEGIN
  SELECT string_agg(
           format('%I.%I', table_record.relname, constraint_record.conname),
           ', ' ORDER BY table_record.relname, constraint_record.conname
         )
    INTO vulnerable_constraints
    FROM pg_constraint AS constraint_record
    JOIN pg_class AS table_record
      ON table_record.oid = constraint_record.conrelid
    JOIN pg_namespace AS namespace_record
      ON namespace_record.oid = table_record.relnamespace
   WHERE namespace_record.nspname = 'architecture_core'
     AND constraint_record.contype = 'c'
     AND pg_get_constraintdef(constraint_record.oid) LIKE
         '%uuid_extract_version%'
     AND pg_get_constraintdef(constraint_record.oid) NOT LIKE
         '%IS NOT DISTINCT FROM 7%';

  IF vulnerable_constraints IS NOT NULL THEN
    RAISE EXCEPTION
      'UUIDv7 CHECK constraints still allow SQL UNKNOWN: %',
      vulnerable_constraints;
  END IF;
END;
$$;
