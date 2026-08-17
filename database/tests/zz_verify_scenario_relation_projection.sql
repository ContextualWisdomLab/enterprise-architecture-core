\set ON_ERROR_STOP on

-- Buyer acceptance for relation-aware target-state scenarios.
-- This file intentionally lands before migration 0013 so the first branch head
-- is RED at the missing relation-delta table/projector boundary.

DO $$
BEGIN
  IF to_regclass('architecture_core.scenario_relation_delta') IS NULL THEN
    RAISE EXCEPTION 'scenario relation delta table is missing';
  END IF;

  IF to_regprocedure('architecture_core.project_scenario_relations(uuid)') IS NULL THEN
    RAISE EXCEPTION 'scenario relation projector is missing';
  END IF;
END;
$$;

-- Give the baseline capability an authoritative revision before this scenario
-- captures its immutable system-time cutoff.
INSERT INTO architecture_core.object_revision (
    tenant_record_id, object_revision_id, architecture_object_id,
    revision_number, object_title, valid_from, truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196d001-1111-7111-8111-111111111111',
    '0195d145-64e8-7f4f-8a23-a0cc784cb901',
    1, 'Order Fulfillment', '2026-01-01T00:00:00Z', 'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

-- Baseline application -> technology relation used by the target-state test.
INSERT INTO architecture_core.architecture_relation (
    tenant_record_id, architecture_relation_id, relation_type_id,
    source_object_id, target_object_id, valid_from, truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196d002-1111-7111-8111-111111111111',
    '0195d145-64e8-7f4f-8a23-a0cc784cb812',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0195d145-64e8-7f4f-8a23-a0cc784cb903',
    '2026-01-01T00:00:00Z', 'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.architecture_scenario (
    tenant_record_id, architecture_scenario_id, scenario_code, scenario_title,
    scenario_description, target_valid_at, valid_from, valid_to,
    truth_status_code, evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196d010-1111-7111-8111-111111111111',
    'modernize_relation_topology', 'Modernize relation topology',
    'Project relation changes without mutating authoritative architecture facts.',
    '2027-10-01T00:00:00Z', '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z', 'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.scenario_baseline (
    tenant_record_id, scenario_baseline_id, architecture_scenario_id,
    baseline_valid_at, baseline_recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196d011-1111-7111-8111-111111111111',
    '0196d010-1111-7111-8111-111111111111',
    '2026-06-15T00:00:00Z', statement_timestamp()
);

-- The replacement technology is introduced in the target state while the
-- legacy technology is removed. Relation projection must respect this object
-- projection instead of emitting a dangling active edge.
INSERT INTO architecture_core.scenario_object_delta (
    tenant_record_id, scenario_object_delta_id, architecture_scenario_id,
    sequence_number, architecture_object_id, desired_presence_code,
    effective_from, truth_status_code, evidence_record_id
) VALUES
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196d020-1111-7111-8111-111111111111',
     '0196d010-1111-7111-8111-111111111111', 1,
     '0196c002-1111-7111-8111-111111111111', 'present',
     '2027-03-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196d020-1111-7111-8111-111111111112',
     '0196d010-1111-7111-8111-111111111111', 2,
     '0195d145-64e8-7f4f-8a23-a0cc784cb903', 'absent',
     '2027-03-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10');

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.scenario_relation_delta (
        tenant_record_id, scenario_relation_delta_id, architecture_scenario_id,
        sequence_number, relation_type_id, source_object_id, target_object_id,
        desired_presence_code, effective_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196d030-1111-7111-8111-111111111110',
        '0196d010-1111-7111-8111-111111111111', 1,
        '0195d145-64e8-7f4f-8a23-a0cc784cb812',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196c002-1111-7111-8111-111111111111', 'present',
        '2027-03-01T00:00:00Z', 'authoritative'
    );
    RAISE EXCEPTION 'authoritative relation delta without evidence was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.scenario_relation_delta (
    tenant_record_id, scenario_relation_delta_id, architecture_scenario_id,
    sequence_number, relation_type_id, source_object_id, target_object_id,
    desired_presence_code, effective_from, truth_status_code,
    evidence_record_id
) VALUES
    -- A later present intent for the legacy relation must still project absent
    -- because its target object is absent in the final object projection.
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196d030-1111-7111-8111-111111111111',
     '0196d010-1111-7111-8111-111111111111', 1,
     '0195d145-64e8-7f4f-8a23-a0cc784cb812',
     '0195d145-64e8-7f4f-8a23-a0cc784cb902',
     '0195d145-64e8-7f4f-8a23-a0cc784cb903', 'absent',
     '2027-03-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196d030-1111-7111-8111-111111111112',
     '0196d010-1111-7111-8111-111111111111', 2,
     '0195d145-64e8-7f4f-8a23-a0cc784cb812',
     '0195d145-64e8-7f4f-8a23-a0cc784cb902',
     '0195d145-64e8-7f4f-8a23-a0cc784cb903', 'present',
     '2027-04-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10'),
    ('0195d145-64e8-7f4f-8a23-a0cc784cb711',
     '0196d030-1111-7111-8111-111111111113',
     '0196d010-1111-7111-8111-111111111111', 3,
     '0195d145-64e8-7f4f-8a23-a0cc784cb812',
     '0195d145-64e8-7f4f-8a23-a0cc784cb902',
     '0196c002-1111-7111-8111-111111111111', 'present',
     '2027-04-01T00:00:00Z', 'authoritative',
     '0195d145-64e8-7f4f-8a23-a0cc784cbf10');

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.scenario_relation_delta (
        tenant_record_id, scenario_relation_delta_id, architecture_scenario_id,
        sequence_number, relation_type_id, source_object_id, target_object_id,
        desired_presence_code, effective_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196d030-1111-7111-8111-111111111114',
        '0196d010-1111-7111-8111-111111111111', 3,
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901', 'present',
        '2027-04-01T00:00:00Z', 'proposed'
    );
    RAISE EXCEPTION 'duplicate relation delta sequence was accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.scenario_relation_delta (
        tenant_record_id, scenario_relation_delta_id, architecture_scenario_id,
        sequence_number, relation_type_id, source_object_id, target_object_id,
        desired_presence_code, effective_from, truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196d030-1111-7111-8111-111111111115',
        '0196d010-1111-7111-8111-111111111111', 4,
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901', 'present',
        '2027-04-01T00:00:00Z', 'proposed'
    );
    RAISE EXCEPTION 'relation delta endpoint type mismatch was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.scenario_relation_delta
       SET desired_presence_code = 'absent'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND scenario_relation_delta_id = '0196d030-1111-7111-8111-111111111113';
    RAISE EXCEPTION 'scenario relation delta meaning was mutable';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END;
$$;

SELECT set_config('app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711', false);

DO $$
DECLARE
  baseline_support_present boolean;
  baseline_support_origin text;
  legacy_present boolean;
  legacy_sequence integer;
  legacy_endpoint_state text;
  replacement_present boolean;
  replacement_origin text;
  replacement_endpoint_state text;
BEGIN
  SELECT is_present, projection_origin_code
    INTO baseline_support_present, baseline_support_origin
    FROM architecture_core.project_scenario_relations(
        '0196d010-1111-7111-8111-111111111111')
   WHERE relation_type_id = '0195d145-64e8-7f4f-8a23-a0cc784cb811'
     AND source_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902'
     AND target_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb901';
  IF baseline_support_present IS DISTINCT FROM true
     OR baseline_support_origin IS DISTINCT FROM 'baseline' THEN
    RAISE EXCEPTION 'unchanged baseline relation projected incorrectly: %, %',
      baseline_support_present, baseline_support_origin;
  END IF;

  SELECT is_present, applied_sequence_number, endpoint_integrity_code
    INTO legacy_present, legacy_sequence, legacy_endpoint_state
    FROM architecture_core.project_scenario_relations(
        '0196d010-1111-7111-8111-111111111111')
   WHERE relation_type_id = '0195d145-64e8-7f4f-8a23-a0cc784cb812'
     AND source_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902'
     AND target_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb903';
  IF legacy_present IS DISTINCT FROM false
     OR legacy_sequence <> 2
     OR legacy_endpoint_state IS DISTINCT FROM 'target_absent' THEN
    RAISE EXCEPTION 'dangling legacy relation was not suppressed: %, %, %',
      legacy_present, legacy_sequence, legacy_endpoint_state;
  END IF;

  SELECT is_present, projection_origin_code, endpoint_integrity_code
    INTO replacement_present, replacement_origin, replacement_endpoint_state
    FROM architecture_core.project_scenario_relations(
        '0196d010-1111-7111-8111-111111111111')
   WHERE relation_type_id = '0195d145-64e8-7f4f-8a23-a0cc784cb812'
     AND source_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902'
     AND target_object_id = '0196c002-1111-7111-8111-111111111111';
  IF replacement_present IS DISTINCT FROM true
     OR replacement_origin IS DISTINCT FROM 'scenario_delta'
     OR replacement_endpoint_state IS DISTINCT FROM 'valid' THEN
    RAISE EXCEPTION 'replacement target-state relation projected incorrectly: %, %, %',
      replacement_present, replacement_origin, replacement_endpoint_state;
  END IF;
END;
$$;

SET ROLE ea_runtime;
SELECT set_config('app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711', false);

DO $$
DECLARE
  visible_delta_count integer;
BEGIN
  SELECT count(*) INTO visible_delta_count
    FROM architecture_core.scenario_relation_delta;
  IF visible_delta_count <> 3 THEN
    RAISE EXCEPTION 'scenario relation RLS exposed % rows', visible_delta_count;
  END IF;
END;
$$;

RESET ROLE;
