\set ON_ERROR_STOP on

-- Buyer acceptance for the purpose-bound runtime query port. Check the
-- migration-time ACL first, before deployment bootstrap repairs the broad RLS
-- fixture role, so an in-place upgrade cannot silently retain PostgreSQL's
-- default PUBLIC EXECUTE on a newly created projector.

DO $$
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

RESET ROLE;
