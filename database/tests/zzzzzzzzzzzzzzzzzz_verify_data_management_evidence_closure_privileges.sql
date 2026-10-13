\set ON_ERROR_STOP on

-- SECURITY DEFINER integration ports must never retain PostgreSQL's default
-- PUBLIC EXECUTE grant. This slice has no runtime HTTP writer yet, so no runtime
-- role is granted the command directly either. Security-sensitive functions
-- also pin their search path, and the published database comment must preserve
-- the evidence-acceptance, atomic-outbox, replay, and runtime-authority contract.

DO $$
DECLARE
  public_execute_count integer;
BEGIN
  SELECT count(*)
    INTO public_execute_count
    FROM pg_proc AS procedure_record
    JOIN pg_namespace AS namespace_record
      ON namespace_record.oid = procedure_record.pronamespace
    CROSS JOIN LATERAL aclexplode(
      coalesce(
        procedure_record.proacl,
        acldefault('f', procedure_record.proowner)
      )
    ) AS privilege_record
   WHERE namespace_record.nspname = 'architecture_core'
     AND procedure_record.proname IN (
       'accept_data_management_improvement_evidence',
       'reject_data_management_closure_mutation'
     )
     AND privilege_record.grantee = 0
     AND privilege_record.privilege_type = 'EXECUTE';

  IF public_execute_count <> 0 THEN
    RAISE EXCEPTION
      'evidence-closure SECURITY DEFINER boundary exposes PUBLIC EXECUTE: %',
      public_execute_count;
  END IF;
END;
$$;

DO $$
DECLARE
  unsafe_function_names text;
BEGIN
  SELECT string_agg(
           procedure_record.proname || '(' ||
           pg_get_function_identity_arguments(procedure_record.oid) || ')',
           ', ' ORDER BY procedure_record.proname
         )
    INTO unsafe_function_names
    FROM pg_proc AS procedure_record
    JOIN pg_namespace AS namespace_record
      ON namespace_record.oid = procedure_record.pronamespace
   WHERE namespace_record.nspname = 'architecture_core'
     AND procedure_record.proname IN (
       'accept_data_management_improvement_evidence',
       'reject_data_management_closure_mutation'
     )
     AND NOT (
       coalesce(procedure_record.proconfig, ARRAY[]::text[]) @>
       ARRAY['search_path=pg_catalog']::text[]
     );

  IF unsafe_function_names IS NOT NULL THEN
    RAISE EXCEPTION
      'evidence-closure functions must pin search_path=pg_catalog: %',
      unsafe_function_names;
  END IF;
END;
$$;

DO $$
DECLARE
  command_comment text;
BEGIN
  SELECT obj_description(procedure_record.oid, 'pg_proc')
    INTO command_comment
    FROM pg_proc AS procedure_record
    JOIN pg_namespace AS namespace_record
      ON namespace_record.oid = procedure_record.pronamespace
   WHERE namespace_record.nspname = 'architecture_core'
     AND procedure_record.proname = 'accept_data_management_improvement_evidence';

  IF command_comment IS NULL
     OR command_comment NOT ILIKE '%authoritative or observed%'
     OR command_comment NOT ILIKE '%transactional outbox%'
     OR command_comment NOT ILIKE '%replay%'
     OR command_comment NOT ILIKE '%PUBLIC execution is revoked%'
     OR command_comment NOT ILIKE '%runtime writer authority%' THEN
    RAISE EXCEPTION
      'evidence-closure command comment lost acceptance, atomicity, replay, or authority semantics: %',
      coalesce(command_comment, '<missing>');
  END IF;
END;
$$;
