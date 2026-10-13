\set ON_ERROR_STOP on

-- Buyer acceptance for immutable-baseline, ordered-delta target-state scenarios.
-- This test intentionally lands before migration 0012 so the first branch head
-- is RED at the missing scenario tables/function boundary.

DO $$
DECLARE
  missing_object_count integer;
BEGIN
  SELECT count(*)
    INTO missing_object_count
    FROM (VALUES
      ('architecture_scenario'),
      ('scenario_baseline'),
      ('scenario_object_delta')
    ) AS required_object(object_name)
   WHERE to_regclass('architecture_core.' || required_object.object_name) IS NULL;

  IF missing_object_count <> 0 THEN
    RAISE EXCEPTION 'scenario projection tables missing: %', missing_object_count;
  END IF;

  IF to_regprocedure('architecture_core.project_scenario_objects(uuid)') IS NULL THEN
    RAISE EXCEPTION 'scenario object projector is missing';
  END IF;
END;
$$;

INSERT INTO architecture_core.object_revision (
    tenant_record_id, object_revision_id, architecture_object_id,
    revision_number, object_title, valid_from, truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c001-1111-7111-8111-111111111111',
    '0195d145-64e8-7f4f-8a23-a0cc784cb903',
    1, 'Acme Database 12', '2026-01-01T00:00:00Z', 'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.architecture_object (
    tenant_record_id, architecture_object_id, object_type_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c002-1111-7111-8111-111111111111',
    '0195d145-64e8-7f4f-8a23-a0cc784cb803'
);

INSERT INTO architecture_core.technology_component (
    tenant_record_id, architecture_object_id, component_code,
    component_category_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c002-1111-7111-8111-111111111111',
    'acme_database_20', 'database_platform'
);

INSERT INTO architecture_core.object_revision (
    tenant_record_id, object_revision_id, architecture_object_id,
    revision_number, object_title, valid_from, truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c003-1111-7111-8111-111111111111',
    '0196c002-1111-7111-8111-111111111111',
    1, 'Acme Database 20', '2026-01-01T00:00:00Z', 'proposed'
);

INSERT INTO architecture_core.architecture_object (
    tenant_record_id, architecture_object_id, object_type_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb712',
    '0196c004-1111-7111-8111-111111111111',
    '0195d145-64e8-7f4f-8a23-a0cc784cb803'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_scenario (
        tenant_record_id, architecture_scenario_id, scenario_code,
        scenario_title, target_valid_at, valid_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196c010-1111-7111-8111-111111111110',
        'modernize_order_platform', 'Modernize order platform',
        '2027-10-01T00:00:00Z', '2026-08-01T00:00:00Z', 'authoritative'
    );
    RAISE EXCEPTION 'authoritative scenario without evidence was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.architecture_scenario (
    tenant_record_id, architecture_scenario_id, scenario_code, scenario_title,
    scenario_description, target_valid_at, valid_from, valid_to,
    truth_status_code, evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c010-1111-7111-8111-111111111111',
    'modernize_order_platform', 'Modernize order platform',
    'Compare the approved target state with the recorded architecture baseline.',
    '2027-10-01T00:00:00Z', '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z', 'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.scenario_baseline (
    tenant_record_id, scenario_baseline_id, architecture_scenario_id,
    baseline_valid_at, baseline_recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c011-1111-7111-8111-111111111111',
    '0196c010-1111-7111-8111-111111111111',
    '2026-06-15T00:00:00Z', statement_timestamp()
);

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.scenario_baseline
       SET baseline_valid_at = '2026-07-01T00:00:00Z'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND scenario_baseline_id = '0196c011-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'scenario baseline was mutable';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.scenario_object_delta (
    tenant_record_id, scenario_object_delta_id, architecture_scenario_id,
    sequence_number, architecture_object_id, desired_presence_code,
    effective_from, truth_status_code, evidence_record_id
) VALUES
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196c020-1111-7111-8111-111111111111',
     '0196c010-1111-7111-8111-111111111111', 1,
     '0195d145-64e8-7f4f-8a23-a0cc784cb903', 'absent',
     '2027-01-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196c020-1111-7111-8111-111111111112',
     '0196c010-1111-7111-8111-111111111111', 2,
     '0195d145-64e8-7f4f-8a23-a0cc784cb903', 'present',
     '2027-02-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196c020-1111-7111-8111-111111111113',
     '0196c010-1111-7111-8111-111111111111', 3,
     '0195d145-64e8-7f4f-8a23-a0cc784cb903', 'absent',
     '2027-03-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196c020-1111-7111-8111-111111111114',
     '0196c010-1111-7111-8111-111111111111', 4,
     '0196c002-1111-7111-8111-111111111111', 'present',
     '2027-03-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10');

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.scenario_object_delta (
        tenant_record_id, scenario_object_delta_id, architecture_scenario_id,
        sequence_number, architecture_object_id, desired_presence_code,
        effective_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196c020-1111-7111-8111-111111111115',
        '0196c010-1111-7111-8111-111111111111', 4,
        '0195d145-64e8-7f4f-8a23-a0cc784cb902', 'absent',
        '2027-03-01T00:00:00Z', 'proposed'
    );
    RAISE EXCEPTION 'duplicate scenario delta sequence was accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.scenario_object_delta (
        tenant_record_id, scenario_object_delta_id, architecture_scenario_id,
        sequence_number, architecture_object_id, desired_presence_code,
        effective_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196c020-1111-7111-8111-111111111116',
        '0196c010-1111-7111-8111-111111111111', 5,
        '0196c004-1111-7111-8111-111111111111', 'present',
        '2027-03-01T00:00:00Z', 'proposed'
    );
    RAISE EXCEPTION 'cross-tenant scenario target was accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.scenario_object_delta
       SET desired_presence_code = 'present'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND scenario_object_delta_id = '0196c020-1111-7111-8111-111111111113';
    RAISE EXCEPTION 'scenario delta meaning was mutable';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END;
$$;

SELECT set_config('app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711', false);

DO $$
DECLARE
  application_present boolean;
  application_origin text;
  legacy_present boolean;
  legacy_sequence integer;
  replacement_present boolean;
  replacement_origin text;
  replacement_truth text;
BEGIN
  SELECT is_present, projection_origin_code
    INTO application_present, application_origin
    FROM architecture_core.project_scenario_objects(
        '0196c010-1111-7111-8111-111111111111')
   WHERE architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902';
  IF application_present IS DISTINCT FROM true
     OR application_origin IS DISTINCT FROM 'baseline' THEN
    RAISE EXCEPTION 'unchanged baseline application projected incorrectly: %, %',
      application_present, application_origin;
  END IF;

  SELECT is_present, applied_sequence_number
    INTO legacy_present, legacy_sequence
    FROM architecture_core.project_scenario_objects(
        '0196c010-1111-7111-8111-111111111111')
   WHERE architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb903';
  IF legacy_present IS DISTINCT FROM false OR legacy_sequence <> 3 THEN
    RAISE EXCEPTION 'latest ordered legacy-technology delta did not win: %, %',
      legacy_present, legacy_sequence;
  END IF;

  SELECT is_present, projection_origin_code, projection_truth_status_code
    INTO replacement_present, replacement_origin, replacement_truth
    FROM architecture_core.project_scenario_objects(
        '0196c010-1111-7111-8111-111111111111')
   WHERE architecture_object_id = '0196c002-1111-7111-8111-111111111111';
  IF replacement_present IS DISTINCT FROM true
     OR replacement_origin IS DISTINCT FROM 'scenario_delta'
     OR replacement_truth IS DISTINCT FROM 'authoritative' THEN
    RAISE EXCEPTION 'replacement technology projection incorrect: %, %, %',
      replacement_present, replacement_origin, replacement_truth;
  END IF;
END;
$$;

DO $$
DECLARE
  current_present boolean;
  current_sequence integer;
  historical_present boolean;
  historical_sequence integer;
  historical_scenario_count integer;
BEGIN
  UPDATE architecture_core.scenario_object_delta
     SET superseded_at = '2100-01-01T00:00:00Z'
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND scenario_object_delta_id = '0196c020-1111-7111-8111-111111111113';

  SELECT is_present, applied_sequence_number
    INTO current_present, current_sequence
    FROM architecture_core.project_scenario_objects(
        '0196c010-1111-7111-8111-111111111111')
   WHERE architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb903';

  SELECT is_present, applied_sequence_number
    INTO historical_present, historical_sequence
    FROM architecture_core.project_scenario_objects_at(
        '0196c010-1111-7111-8111-111111111111',
        '2099-01-01T00:00:00Z')
   WHERE architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb903';

  IF current_present IS DISTINCT FROM true
     OR current_sequence <> 2
     OR historical_present IS DISTINCT FROM false
     OR historical_sequence <> 3 THEN
    RAISE EXCEPTION
      'current projection did not hide superseded delta while preserving history: %, %, %, %',
      current_present, current_sequence, historical_present, historical_sequence;
  END IF;

  UPDATE architecture_core.architecture_scenario
     SET superseded_at = '2100-01-01T00:00:00Z'
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_scenario_id = '0196c010-1111-7111-8111-111111111111';

  BEGIN
    PERFORM 1
      FROM architecture_core.project_scenario_objects(
          '0196c010-1111-7111-8111-111111111111');
    RAISE EXCEPTION 'current projection exposed a superseded scenario';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*)
    INTO historical_scenario_count
    FROM architecture_core.project_scenario_objects_at(
        '0196c010-1111-7111-8111-111111111111',
        '2099-01-01T00:00:00Z');
  IF historical_scenario_count = 0 THEN
    RAISE EXCEPTION 'historical projection lost a scenario before supersession';
  END IF;
END;
$$;

SET ROLE ea_runtime;
SELECT set_config('app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711', false);

DO $$
DECLARE
  visible_scenario_count integer;
BEGIN
  SELECT count(*) INTO visible_scenario_count
    FROM architecture_core.architecture_scenario;
  IF visible_scenario_count <> 1 THEN
    RAISE EXCEPTION 'scenario RLS exposed % rows', visible_scenario_count;
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_scenario (
        tenant_record_id, architecture_scenario_id, scenario_code,
        scenario_title, target_valid_at, valid_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        '0196c010-1111-7111-8111-111111111112',
        'foreign_tenant_scenario', 'Foreign tenant scenario',
        '2027-10-01T00:00:00Z', '2026-08-01T00:00:00Z', 'proposed'
    );
    RAISE EXCEPTION 'cross-tenant scenario insert unexpectedly succeeded';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END;
$$;

RESET ROLE;
