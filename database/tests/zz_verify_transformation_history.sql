\set ON_ERROR_STOP on

-- Buyer acceptance for approved transformation execution history. This test
-- intentionally lands before migration 0014 so the first branch head is RED
-- at the missing transformation tables/projector boundary.

DO $$
DECLARE
  missing_object_count integer;
BEGIN
  SELECT count(*)
    INTO missing_object_count
    FROM (VALUES
      ('architecture_core.architecture_transformation'),
      ('architecture_core.transformation_history_record')
    ) AS required_object(object_name)
   WHERE to_regclass(required_object.object_name) IS NULL;

  IF missing_object_count <> 0 THEN
    RAISE EXCEPTION 'transformation history tables missing: %', missing_object_count;
  END IF;

  IF to_regprocedure(
      'architecture_core.project_transformation_state(uuid,timestamptz,timestamptz)'
     ) IS NULL THEN
    RAISE EXCEPTION 'bitemporal transformation state projector is missing';
  END IF;
END;
$$;

INSERT INTO architecture_core.remediation_initiative (
    tenant_record_id,
    remediation_initiative_id,
    initiative_code,
    initiative_title,
    initiative_description,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e001-1111-7111-8111-111111111111',
    'retire_legacy_database',
    'Retire legacy database',
    'Execute the approved target-state change without rewriting prior decisions.',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.architecture_scenario (
    tenant_record_id,
    architecture_scenario_id,
    scenario_code,
    scenario_title,
    scenario_description,
    target_valid_at,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e002-1111-7111-8111-111111111111',
    'approved_database_target',
    'Approved database target',
    'Target state used to govern the transformation execution history.',
    '2027-12-01T00:00:00Z',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.scenario_baseline (
    tenant_record_id,
    scenario_baseline_id,
    architecture_scenario_id,
    baseline_valid_at,
    baseline_recorded_at,
    recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e003-1111-7111-8111-111111111111',
    '0196e002-1111-7111-8111-111111111111',
    '2026-07-01T00:00:00Z',
    '2026-08-01T00:00:00Z',
    '2026-08-01T00:00:01Z'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_transformation (
        tenant_record_id,
        architecture_transformation_id,
        architecture_scenario_id,
        remediation_initiative_id,
        transformation_code,
        transformation_title,
        valid_from,
        valid_to,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111110',
        '0196e002-1111-7111-8111-111111111111',
        '0196e001-1111-7111-8111-111111111111',
        'database_target_transition',
        'Database target transition',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        'authoritative'
    );
    RAISE EXCEPTION 'authoritative transformation without evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.architecture_transformation (
    tenant_record_id,
    architecture_transformation_id,
    architecture_scenario_id,
    remediation_initiative_id,
    transformation_code,
    transformation_title,
    transformation_description,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e010-1111-7111-8111-111111111111',
    '0196e002-1111-7111-8111-111111111111',
    '0196e001-1111-7111-8111-111111111111',
    'database_target_transition',
    'Database target transition',
    'Bind an approved EA target state to its remediation initiative and history.',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    '2026-08-02T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.transformation_history_record (
    tenant_record_id,
    transformation_history_record_id,
    architecture_transformation_id,
    sequence_number,
    transformation_state_code,
    effective_at,
    recorded_at,
    decision_actor_ref,
    decision_reason_text,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e020-1111-7111-8111-111111111111',
    '0196e010-1111-7111-8111-111111111111',
    1,
    'proposed',
    '2026-09-01T00:00:00Z',
    '2026-09-01T01:00:00Z',
    'urn:cwl:actor:architecture-board',
    'Target-state evidence is ready for architecture-board approval.',
    'proposed'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.transformation_history_record (
        tenant_record_id,
        transformation_history_record_id,
        architecture_transformation_id,
        sequence_number,
        transformation_state_code,
        effective_at,
        recorded_at,
        decision_actor_ref,
        decision_reason_text,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e020-1111-7111-8111-111111111112',
        '0196e010-1111-7111-8111-111111111111',
        2,
        'approved',
        '2026-10-01T00:00:00Z',
        '2026-10-02T00:00:00Z',
        'urn:cwl:actor:architecture-board',
        'Approval cannot be inferred or proposed.',
        'proposed'
    );
    RAISE EXCEPTION 'proposed evidence silently became an approval';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.transformation_history_record (
    tenant_record_id,
    transformation_history_record_id,
    architecture_transformation_id,
    sequence_number,
    transformation_state_code,
    effective_at,
    recorded_at,
    decision_actor_ref,
    decision_reason_text,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e020-1111-7111-8111-111111111113',
    '0196e010-1111-7111-8111-111111111111',
    2,
    'approved',
    '2026-10-01T00:00:00Z',
    '2026-10-02T00:00:00Z',
    'urn:cwl:actor:architecture-board',
    'The reviewed target state and remediation initiative are approved.',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.transformation_history_record (
        tenant_record_id,
        transformation_history_record_id,
        architecture_transformation_id,
        sequence_number,
        transformation_state_code,
        effective_at,
        recorded_at,
        decision_actor_ref,
        decision_reason_text,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e020-1111-7111-8111-111111111114',
        '0196e010-1111-7111-8111-111111111111',
        3,
        'completed',
        '2027-01-01T00:00:00Z',
        '2027-01-02T00:00:00Z',
        'urn:cwl:actor:platform-operations',
        'Completion cannot skip the started state.',
        'observed',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );
    RAISE EXCEPTION 'invalid transformation transition was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.transformation_history_record (
    tenant_record_id,
    transformation_history_record_id,
    architecture_transformation_id,
    sequence_number,
    transformation_state_code,
    effective_at,
    recorded_at,
    decision_actor_ref,
    decision_reason_text,
    truth_status_code,
    evidence_record_id
) VALUES
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196e020-1111-7111-8111-111111111115',
     '0196e010-1111-7111-8111-111111111111',
     3, 'started', '2027-01-01T00:00:00Z', '2027-01-02T00:00:00Z',
     'urn:cwl:actor:platform-operations',
     'Execution began after the approved change window opened.',
     'observed', '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196e020-1111-7111-8111-111111111116',
     '0196e010-1111-7111-8111-111111111111',
     4, 'completed', '2027-06-01T00:00:00Z', '2027-06-02T00:00:00Z',
     'urn:cwl:actor:platform-operations',
     'Target-state execution completed with retained evidence.',
     'observed', '0195d145-64e8-7f4f-8a23-a0cc784cbf10');

DO $$
DECLARE
  state_at_valid_cutoff text;
  state_at_recording_cutoff text;
  state_after_start text;
  state_after_completion text;
BEGIN
  SELECT transformation_state_code
    INTO state_at_valid_cutoff
    FROM architecture_core.project_transformation_state(
      '0196e010-1111-7111-8111-111111111111',
      '2026-09-15T00:00:00Z',
      '2028-01-01T00:00:00Z'
    );
  IF state_at_valid_cutoff IS DISTINCT FROM 'proposed' THEN
    RAISE EXCEPTION 'valid-time projection returned %', state_at_valid_cutoff;
  END IF;

  SELECT transformation_state_code
    INTO state_at_recording_cutoff
    FROM architecture_core.project_transformation_state(
      '0196e010-1111-7111-8111-111111111111',
      '2027-02-01T00:00:00Z',
      '2026-10-01T12:00:00Z'
    );
  IF state_at_recording_cutoff IS DISTINCT FROM 'proposed' THEN
    RAISE EXCEPTION 'system-time projection returned %', state_at_recording_cutoff;
  END IF;

  SELECT transformation_state_code
    INTO state_after_start
    FROM architecture_core.project_transformation_state(
      '0196e010-1111-7111-8111-111111111111',
      '2027-02-01T00:00:00Z',
      '2027-02-01T00:00:00Z'
    );
  IF state_after_start IS DISTINCT FROM 'started' THEN
    RAISE EXCEPTION 'started state projection returned %', state_after_start;
  END IF;

  SELECT transformation_state_code
    INTO state_after_completion
    FROM architecture_core.project_transformation_state(
      '0196e010-1111-7111-8111-111111111111',
      '2027-07-01T00:00:00Z',
      '2027-07-01T00:00:00Z'
    );
  IF state_after_completion IS DISTINCT FROM 'completed' THEN
    RAISE EXCEPTION 'completed state projection returned %', state_after_completion;
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.transformation_history_record
       SET transformation_state_code = 'cancelled'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND transformation_history_record_id =
           '0196e020-1111-7111-8111-111111111116';
    RAISE EXCEPTION 'transformation history meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  visible_transformation_count integer;
  visible_history_count integer;
BEGIN
  SELECT count(*) INTO visible_transformation_count
    FROM architecture_core.architecture_transformation;
  SELECT count(*) INTO visible_history_count
    FROM architecture_core.transformation_history_record;

  IF visible_transformation_count <> 1 OR visible_history_count <> 4 THEN
    RAISE EXCEPTION 'transformation RLS exposed %, % rows',
      visible_transformation_count, visible_history_count;
  END IF;
END;
$$;

RESET ROLE;
