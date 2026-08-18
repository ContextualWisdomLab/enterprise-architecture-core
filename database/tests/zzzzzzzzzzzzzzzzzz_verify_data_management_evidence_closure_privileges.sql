\set ON_ERROR_STOP on

-- SECURITY DEFINER integration ports must never retain PostgreSQL's default
-- PUBLIC EXECUTE grant. This slice has no runtime HTTP writer yet, so no runtime
-- role is granted the command directly either.

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
