\set ON_ERROR_STOP on

-- Reassessment commands and immutable-history/temporal guards are
-- security-sensitive integration boundaries. They must not expose PUBLIC
-- EXECUTE, and every function in this boundary must pin search_path so later
-- function-body maintenance cannot resolve attacker-controlled objects through
-- a mutable session path.

DO $$
DECLARE
  public_execute_count integer;
  unsafe_function_names text;
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
       'request_data_management_assessment_recheck',
       'request_data_management_assessment_recheck_for_tenant',
       'reject_assessment_recheck_request_mutation',
       'enforce_assessment_recheck_temporal_order'
     )
     AND privilege_record.grantee = 0
     AND privilege_record.privilege_type = 'EXECUTE';

  IF public_execute_count <> 0 THEN
    RAISE EXCEPTION
      'reassessment boundary exposes PUBLIC EXECUTE: %',
      public_execute_count;
  END IF;

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
       'request_data_management_assessment_recheck',
       'request_data_management_assessment_recheck_for_tenant',
       'reject_assessment_recheck_request_mutation',
       'enforce_assessment_recheck_temporal_order'
     )
     AND NOT (
       coalesce(procedure_record.proconfig, ARRAY[]::text[]) @>
       ARRAY['search_path=pg_catalog']::text[]
     );

  IF unsafe_function_names IS NOT NULL THEN
    RAISE EXCEPTION
      'reassessment boundary must pin search_path=pg_catalog: %',
      unsafe_function_names;
  END IF;
END;
$$;
