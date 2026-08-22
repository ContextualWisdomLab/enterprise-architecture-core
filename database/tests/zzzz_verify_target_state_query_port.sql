\set ON_ERROR_STOP on

-- Buyer acceptance for the purpose-bound runtime query port. Check the
-- migration-time ACL first, before deployment bootstrap repairs the broad RLS
-- fixture role, so an in-place upgrade cannot silently retain PostgreSQL's
-- default PUBLIC EXECUTE on a newly created projector.

DO $$
DECLARE
  query_owner text;
BEGIN
  IF to_regprocedure(
      'architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer)'
     ) IS NULL THEN
    RAISE EXCEPTION 'runtime target-state query port is missing';
  END IF;

  IF has_function_privilege(
      'public',
      'architecture_core.project_technology_target_state_plan(uuid,timestamptz,timestamptz,integer)',
      'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'target-state projector retains PUBLIC execute after migration';
  END IF;

  SELECT pg_catalog.pg_get_userbyid(pg_proc.proowner)
    INTO query_owner
    FROM pg_catalog.pg_proc
   WHERE pg_proc.oid = pg_catalog.to_regprocedure(
       'architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer)'
   );

  IF query_owner <> 'ea_function_owner' THEN
    RAISE EXCEPTION
      'target-state query port owner must be ea_function_owner, found %',
      query_owner;
  END IF;

  IF EXISTS (
      SELECT 1
        FROM pg_catalog.pg_roles
       WHERE rolname = 'ea_function_owner'
         AND (rolsuper OR rolbypassrls OR rolcanlogin)
  ) THEN
    RAISE EXCEPTION
      'ea_function_owner must be NOLOGIN NOSUPERUSER NOBYPASSRLS';
  END IF;
END;
$$;

-- Earlier foundation acceptance deliberately grants direct table/function
-- authority to ea_runtime as an RLS probe. Reapply the production deployment
-- boundary before asserting application-runtime privileges; this must strip
-- those fixture-only grants and restore only the purpose-bound query port.
\ir ../init/003_grant_runtime_access.sql

DO $$
BEGIN
  IF NOT has_function_privilege(
      'ea_runtime',
      'architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer)',
      'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'ea_runtime lacks the purpose-bound target-state query port';
  END IF;

  IF has_function_privilege(
      'ea_runtime',
      'architecture_core.project_technology_target_state_plan(uuid,timestamptz,timestamptz,integer)',
      'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'ea_runtime unexpectedly has direct projector authority';
  END IF;

  IF has_table_privilege(
      'ea_runtime',
      'architecture_core.tenant_record',
      'SELECT,INSERT,UPDATE,DELETE'
  ) THEN
    RAISE EXCEPTION 'ea_runtime unexpectedly has direct application-table authority';
  END IF;
END;
$$;

SET ROLE ea_runtime;

DO $$
DECLARE
  runtime_plan_visible boolean;
BEGIN
  SELECT (
      count(*) > 0
      AND bool_and(recommended_action_code IS NOT NULL)
      AND bool_and(decision_readiness_code IS NOT NULL)
  )
  INTO runtime_plan_visible
  FROM architecture_core.read_technology_target_state_plan(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196f100-1111-7111-8111-111111111111',
      '2027-02-01T00:00:00Z',
      '2027-02-01T00:00:00Z',
      180
  );

  IF NOT coalesce(runtime_plan_visible, false) THEN
    RAISE EXCEPTION 'purpose-bound runtime query did not return buyer decision evidence';
  END IF;
END;
$$;

-- A verified tenant that does not own the requested technology must be denied
-- by the underlying tenant-scoped projector. Pin both the CHECK_VIOLATION
-- SQLSTATE and the exact denial message: returning rows would be a leak, while
-- any other exception indicates that the intended authorization boundary drifted.
DO $$
DECLARE
  cross_tenant_denied boolean := false;
BEGIN
  BEGIN
    PERFORM 1
      FROM architecture_core.read_technology_target_state_plan(
          '0195d145-0000-7000-8000-000000000000',
          '0196f100-1111-7111-8111-111111111111',
          '2027-02-01T00:00:00Z',
          '2027-02-01T00:00:00Z',
          180
      );
  EXCEPTION
    WHEN SQLSTATE '23514' THEN
      IF SQLERRM <> 'technology version is unavailable for the active tenant' THEN
        RAISE;
      END IF;
      cross_tenant_denied := true;
  END;

  IF NOT cross_tenant_denied THEN
    RAISE EXCEPTION
      'target-state query port did not deny a cross-tenant technology read';
  END IF;
END;
$$;

RESET ROLE;
