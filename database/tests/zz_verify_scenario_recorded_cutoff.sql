\set ON_ERROR_STOP on

BEGIN;

-- A bitemporal scenario projection must not observe deltas that were recorded
-- after the caller's system-time cutoff. This is distinct from supersession:
-- an append recorded later must be invisible to an earlier historical read.
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.architecture_scenario (
    tenant_record_id,
    architecture_scenario_id,
    scenario_code,
    scenario_title,
    target_valid_at,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196c010-2222-7222-8222-222222222222',
    'recorded_cutoff_regression',
    'Recorded cutoff regression',
    '2027-10-01T00:00:00Z',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    '2026-08-01T00:00:00Z',
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
    '0196c011-2222-7222-8222-222222222222',
    '0196c010-2222-7222-8222-222222222222',
    '2026-07-15T00:00:00Z',
    '2026-07-15T00:00:00Z',
    '2026-08-02T00:00:00Z'
);

INSERT INTO architecture_core.scenario_object_delta (
    tenant_record_id,
    scenario_object_delta_id,
    architecture_scenario_id,
    sequence_number,
    architecture_object_id,
    desired_presence_code,
    effective_from,
    recorded_at,
    truth_status_code,
    evidence_record_id
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196c020-2222-7222-8222-222222222221',
        '0196c010-2222-7222-8222-222222222222',
        1,
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        'present',
        '2027-01-01T00:00:00Z',
        '2026-08-03T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196c020-2222-7222-8222-222222222222',
        '0196c010-2222-7222-8222-222222222222',
        2,
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        'absent',
        '2027-02-01T00:00:00Z',
        '2026-08-05T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

DO $$
DECLARE
  projected_present boolean;
  projected_sequence integer;
BEGIN
  SELECT is_present, applied_sequence_number
    INTO projected_present, projected_sequence
    FROM architecture_core.project_scenario_objects_at(
        '0196c010-2222-7222-8222-222222222222',
        '2026-08-04T00:00:00Z'
    )
   WHERE architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb903';

  IF projected_present IS DISTINCT FROM true OR projected_sequence <> 1 THEN
    RAISE EXCEPTION
      'historical scenario projection leaked a later-recorded delta: %, %',
      projected_present,
      projected_sequence;
  END IF;
END;
$$;

ROLLBACK;
