\set ON_ERROR_STOP on

-- An improvement plan stores both the remediation initiative and its milestone.
-- The database must reject a milestone owned by a different initiative even when
-- every individual tenant/object foreign key is otherwise valid. Build a fresh,
-- active assessment gap so source-truth and gap-uniqueness guards cannot mask the
-- pair-integrity failure this acceptance test is intended to prove.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  source_projection_id uuid;
  target_capability_id uuid;
  accountable_organization_id uuid;
  expected_initiative_id uuid;
  other_initiative_id uuid;
  other_milestone_id uuid;
BEGIN
  SELECT
      projection_record.data_management_assessment_projection_id,
      projection_record.subject_capability_object_id
    INTO source_projection_id, target_capability_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.truth_status_code NOT IN ('rejected', 'superseded')
     AND projection_record.superseded_at IS NULL
   ORDER BY projection_record.recorded_at DESC,
            projection_record.data_management_assessment_projection_id DESC
   LIMIT 1;

  SELECT organization_record.architecture_object_id
    INTO accountable_organization_id
    FROM architecture_core.organization_unit AS organization_record
   WHERE organization_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   ORDER BY organization_record.architecture_object_id
   LIMIT 1;

  IF source_projection_id IS NULL
     OR target_capability_id IS NULL
     OR accountable_organization_id IS NULL THEN
    RAISE EXCEPTION 'active assessment/capability/organization fixture is unavailable for pair-integrity acceptance';
  END IF;

  INSERT INTO architecture_core.assessment_missing_evidence_projection (
      tenant_record_id,
      data_management_assessment_projection_id,
      missing_evidence_code
  ) VALUES (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      source_projection_id,
      'pair_guard_evidence'
  );

  INSERT INTO architecture_core.remediation_initiative (
      tenant_record_id,
      initiative_code,
      initiative_title,
      initiative_description,
      valid_from,
      truth_status_code
  ) VALUES (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      'pair_guard_expected',
      'Pair guard expected initiative',
      'Acceptance-only proposed initiative that the improvement plan records.',
      '2026-08-18T00:00:01Z',
      'proposed'
  )
  RETURNING remediation_initiative_id INTO expected_initiative_id;

  INSERT INTO architecture_core.remediation_initiative (
      tenant_record_id,
      initiative_code,
      initiative_title,
      initiative_description,
      valid_from,
      truth_status_code
  ) VALUES (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      'pair_guard_other',
      'Pair guard other initiative',
      'Acceptance-only proposed initiative that owns the mismatched milestone.',
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
      'Acceptance-only milestone belonging to the other probe initiative.',
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
        'pair_guard_evidence',
        '0196f103-1111-7111-8111-111111111199',
        target_capability_id,
        accountable_organization_id,
        expected_initiative_id,
        other_milestone_id
    );
    RAISE EXCEPTION 'improvement plan accepted a milestone from another initiative';
  EXCEPTION WHEN foreign_key_violation THEN
    NULL;
  END;
END;
$$;
