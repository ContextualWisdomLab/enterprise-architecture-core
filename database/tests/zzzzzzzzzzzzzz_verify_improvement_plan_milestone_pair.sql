\set ON_ERROR_STOP on

-- An improvement plan stores both the remediation initiative and its milestone.
-- The database must reject a milestone owned by a different initiative even when
-- every individual tenant/object foreign key is otherwise valid.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  source_projection_id uuid;
  source_initiative_id uuid;
  other_initiative_id uuid;
  other_milestone_id uuid;
BEGIN
  SELECT
      plan_record.data_management_assessment_projection_id,
      plan_record.remediation_initiative_id
    INTO source_projection_id, source_initiative_id
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   ORDER BY plan_record.recorded_at
   LIMIT 1;

  IF source_projection_id IS NULL OR source_initiative_id IS NULL THEN
    RAISE EXCEPTION 'improvement-plan fixture is unavailable for pair-integrity acceptance';
  END IF;

  INSERT INTO architecture_core.remediation_initiative (
      tenant_record_id,
      initiative_code,
      initiative_title,
      initiative_description,
      valid_from,
      truth_status_code
  ) VALUES (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      'pair_guard_probe',
      'Pair guard probe',
      'Acceptance-only proposed initiative for relational pair integrity.',
      '2026-08-18T00:00:01Z',
      'proposed'
  )
  RETURNING remediation_initiative_id INTO other_initiative_id;

  INSERT INTO architecture_core.initiative_milestone (
      tenant_record_id,
      remediation_initiative_id,
      milestone_code,
      milestone_title,
      milestone_description,
      sequence_number,
      target_at,
      valid_from,
      truth_status_code
  ) VALUES (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      other_initiative_id,
      'pair_guard_milestone',
      'Pair guard milestone',
      'Acceptance-only milestone belonging to the probe initiative.',
      1,
      '2026-12-31T00:00:00Z',
      '2026-08-18T00:00:01Z',
      'proposed'
  )
  RETURNING initiative_milestone_id INTO other_milestone_id;

  BEGIN
    INSERT INTO architecture_core.assessment_improvement_plan (
        tenant_record_id,
        data_management_assessment_projection_id,
        missing_evidence_code,
        decision_request_id,
        target_capability_object_id,
        accountable_organization_object_id,
        remediation_initiative_id,
        initiative_milestone_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        source_projection_id,
        'stewardship_evidence',
        '0196f103-1111-7111-8111-111111111199',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '0196f100-1111-7111-8111-111111111110',
        source_initiative_id,
        other_milestone_id
    );
    RAISE EXCEPTION 'improvement plan accepted a milestone from another initiative';
  EXCEPTION WHEN foreign_key_violation THEN
    NULL;
  END;
END;
$$;
