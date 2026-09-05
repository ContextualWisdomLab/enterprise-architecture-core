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

-- A SECURITY DEFINER read may install the verified tenant only inside its own
-- bounded query. Pooled runtime transactions must retain the caller tenant on
-- both a normal return and a raised read, matching the other purpose-bound EA
-- database ports instead of leaking authority into the next operation.
DO $$
DECLARE
  caller_tenant text;
  success_restored boolean;
  failure_restored boolean := false;
  failure_rejected boolean := false;
BEGIN
  caller_tenant := pg_catalog.current_setting('app.tenant_record_id', true);

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      '0195d145-64e8-7f4f-8a23-a0cc784cb712',
      true
  );
  PERFORM *
    FROM architecture_core.read_target_state_monitoring_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        '2027-02-02T00:00:00Z',
        clock_timestamp(),
        90
    );
  success_restored :=
      pg_catalog.current_setting('app.tenant_record_id', true) IS NOT DISTINCT FROM
      '0195d145-64e8-7f4f-8a23-a0cc784cb712';

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      '0195d145-64e8-7f4f-8a23-a0cc784cb712',
      true
  );
  BEGIN
    PERFORM *
      FROM architecture_core.read_target_state_monitoring_status(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111192',
          '2027-02-02T00:00:00Z',
          clock_timestamp(),
          90
      );
  EXCEPTION WHEN check_violation THEN
    failure_rejected := true;
  END;
  failure_restored :=
      pg_catalog.current_setting('app.tenant_record_id', true) IS NOT DISTINCT FROM
      '0195d145-64e8-7f4f-8a23-a0cc784cb712';

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      COALESCE(caller_tenant, ''),
      true
  );

  IF NOT failure_rejected THEN
    RAISE EXCEPTION 'missing target-state monitoring evidence was accepted';
  END IF;
  IF NOT success_restored OR NOT failure_restored THEN
    RAISE EXCEPTION
      'target-state monitoring leaked tenant context: success_restored=%, failure_restored=%',
      success_restored,
      failure_restored;
  END IF;
END;
$$;

-- The freshness threshold is inclusive. Bind the boundary to the latest
-- verification observation so a later append-only re-verification cannot make
-- this acceptance test accidentally exercise an older evidence record.
DO $$
DECLARE
  monitoring_state text;
  buyer_next_action text;
  latest_verification_at timestamptz;
BEGIN
  SELECT max(effective_at)
    INTO latest_verification_at
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND transformation_state_code = 'verified';

  IF latest_verification_at IS NULL THEN
    RAISE EXCEPTION 'monitoring freshness boundary has no verification evidence';
  END IF;

  SELECT monitoring_state_code, next_action
    INTO monitoring_state, buyer_next_action
    FROM architecture_core.read_target_state_monitoring_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        latest_verification_at + interval '90 days',
        clock_timestamp(),
        90
    );

  IF monitoring_state <> 'current'
     OR buyer_next_action <> 'continue_monitoring' THEN
    RAISE EXCEPTION 'verification evidence at the freshness boundary was not current';
  END IF;

  SELECT monitoring_state_code, next_action
    INTO monitoring_state, buyer_next_action
    FROM architecture_core.read_target_state_monitoring_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        latest_verification_at + interval '91 days',
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
