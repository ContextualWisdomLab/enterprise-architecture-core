\set ON_ERROR_STOP on

-- Buyer acceptance for post-verification target-state monitoring.
-- The purpose-bound database port must preserve tenant/time boundaries and fail
-- closed when the caller omits the freshness policy instead of silently
-- classifying stale evidence as current.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.read_target_state_monitoring_status(uuid,uuid,timestamptz,timestamptz,integer)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state monitoring query is missing';
  END IF;
END;
$$;

DO $$
DECLARE
  monitoring_state text;
  buyer_next_action text;
  evidence_age integer;
BEGIN
  SELECT monitoring_state_code, next_action, evidence_age_days
    INTO monitoring_state, buyer_next_action, evidence_age
    FROM architecture_core.read_target_state_monitoring_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        '2027-02-02T00:00:00Z',
        clock_timestamp(),
        90
    );

  IF monitoring_state <> 'current'
     OR buyer_next_action <> 'continue_monitoring'
     OR evidence_age <> 0 THEN
    RAISE EXCEPTION 'fresh verified target-state evidence is not monitored as current';
  END IF;
END;
$$;

DO $$
DECLARE
  monitoring_state text;
  buyer_next_action text;
BEGIN
  SELECT monitoring_state_code, next_action
    INTO monitoring_state, buyer_next_action
    FROM architecture_core.read_target_state_monitoring_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        '2027-05-04T00:00:00Z',
        clock_timestamp(),
        90
    );

  IF monitoring_state <> 'stale'
     OR buyer_next_action <> 'collect_new_target_state_evidence' THEN
    RAISE EXCEPTION 'stale verification evidence did not produce a collection action';
  END IF;
END;
$$;

DO $$
DECLARE
  null_policy_rejected boolean := false;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.read_target_state_monitoring_status(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '2027-05-04T00:00:00Z',
          clock_timestamp(),
          NULL
      );
  EXCEPTION WHEN check_violation THEN
    null_policy_rejected := true;
  END;

  IF NOT null_policy_rejected THEN
    RAISE EXCEPTION 'NULL monitoring freshness policy was accepted';
  END IF;
END;
$$;

DO $$
DECLARE
  cross_tenant_rejected boolean := false;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.read_target_state_monitoring_status(
          '0195d145-64e8-7f4f-8a23-a0cc784cb799',
          '0196e010-1111-7111-8111-111111111191',
          '2027-02-02T00:00:00Z',
          clock_timestamp(),
          90
      );
  EXCEPTION WHEN check_violation THEN
    cross_tenant_rejected := true;
  END;

  IF NOT cross_tenant_rejected THEN
    RAISE EXCEPTION 'cross-tenant target-state monitoring was accepted';
  END IF;
END;
$$;
