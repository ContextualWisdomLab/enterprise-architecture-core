\set ON_ERROR_STOP on

-- RED buyer acceptance for the purpose-bound runtime query port. This test
-- intentionally lands before migration 0021 so the first branch head proves
-- the missing authenticated database boundary rather than a documentation gap.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer)'
     ) IS NULL THEN
    RAISE EXCEPTION 'runtime target-state query port is missing';
  END IF;
END;
$$;

SELECT has_function_privilege(
    'ea_runtime',
    'architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer)',
    'EXECUTE'
) AS runtime_query_execute \gset

\if :runtime_query_execute
\else
  \echo 'ea_runtime lacks the purpose-bound target-state query port'
  \quit 3
\endif

SELECT has_function_privilege(
    'ea_runtime',
    'architecture_core.project_technology_target_state_plan(uuid,timestamptz,timestamptz,integer)',
    'EXECUTE'
) AS direct_projector_execute \gset

\if :direct_projector_execute
  \echo 'ea_runtime unexpectedly has direct projector authority'
  \quit 4
\endif

SET ROLE ea_runtime;

SELECT (
    count(*) > 0
    AND bool_and(recommended_action_code IS NOT NULL)
    AND bool_and(decision_readiness_code IS NOT NULL)
) AS runtime_plan_visible
FROM architecture_core.read_technology_target_state_plan(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f100-1111-7111-8111-111111111111',
    '2027-02-01T00:00:00Z',
    '2027-02-01T00:00:00Z',
    180
) \gset

\if :runtime_plan_visible
\else
  \echo 'purpose-bound runtime query did not return buyer decision evidence'
  \quit 5
\endif

RESET ROLE;
