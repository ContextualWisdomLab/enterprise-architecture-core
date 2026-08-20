\set ON_ERROR_STOP on

-- RED buyer acceptance for issue #25's dependency requirement. The assessment
-- improvement command must accept a bounded dependency/evidence set, persist it
-- as normalized EA-owned decision evidence, and bind exact replay to the same set.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f120-1111-7111-8111-111111111121',
    'urn:cwl:tenant_001:ea_core:initiative_dependency_evidence:0196f120-1111-7111-8111-111111111121',
    repeat('b', 64),
    'https://example.com/evidence/dependency-001'
)
ON CONFLICT DO NOTHING;

INSERT INTO architecture_core.remediation_initiative (
    tenant_record_id,
    remediation_initiative_id,
    initiative_code,
    initiative_title,
    initiative_description,
    valid_from,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f120-1111-7111-8111-111111111122',
    'dependency_foundation_ready',
    'Dependency foundation ready',
    'Existing initiative that must complete before the assessment remediation can proceed.',
    '2026-09-01T00:00:00Z',
    'authoritative',
    '0196f120-1111-7111-8111-111111111121'
)
ON CONFLICT DO NOTHING;

DO $$
DECLARE
  source_projection_id uuid;
  target_capability_id uuid;
  accountable_organization_id uuid;
  inserted_plan_id uuid;
  inserted_initiative_id uuid;
  replay_plan_id uuid;
  dependency_set_count integer;
  dependency_relation_count integer;
BEGIN
  SELECT
      projection_record.data_management_assessment_projection_id,
      projection_record.subject_capability_object_id
    INTO source_projection_id, target_capability_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
    JOIN architecture_core.assessment_missing_evidence_projection AS missing_record
      ON missing_record.tenant_record_id = projection_record.tenant_record_id
     AND missing_record.data_management_assessment_projection_id =
         projection_record.data_management_assessment_projection_id
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.superseded_at IS NULL
     AND projection_record.truth_status_code NOT IN ('rejected', 'superseded')
     AND missing_record.missing_evidence_code = 'stewardship_evidence'
   ORDER BY projection_record.recorded_at DESC
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
    RAISE EXCEPTION 'dependency acceptance fixture is incomplete';
  END IF;

  SELECT
      result.assessment_improvement_plan_id,
      result.remediation_initiative_id
    INTO inserted_plan_id, inserted_initiative_id
    FROM architecture_core.create_data_management_improvement_plan(
      source_projection_id,
      'stewardship_evidence',
      '0196f120-1111-7111-8111-111111111123',
      target_capability_id,
      accountable_organization_id,
      'close_stewardship_dependency_gap',
      'Close stewardship dependency gap',
      'stewardship_dependency_evidence',
      'Stewardship dependency evidence',
      '2027-01-31T00:00:00Z',
      'portfolio://fy2027/data-governance',
      ARRAY['0196f120-1111-7111-8111-111111111122'::uuid],
      ARRAY['0196f120-1111-7111-8111-111111111121'::uuid]
    ) AS result;

  SELECT count(*)
    INTO dependency_set_count
    FROM architecture_core.assessment_improvement_dependency_set AS dependency_set
   WHERE dependency_set.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND dependency_set.assessment_improvement_plan_id = inserted_plan_id
     AND dependency_set.dependency_count = 1;

  SELECT count(*)
    INTO dependency_relation_count
    FROM architecture_core.assessment_improvement_dependency_relation AS dependency_relation
   WHERE dependency_relation.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND dependency_relation.assessment_improvement_plan_id = inserted_plan_id
     AND dependency_relation.prerequisite_initiative_id =
         '0196f120-1111-7111-8111-111111111122'
     AND dependency_relation.dependency_evidence_record_id =
         '0196f120-1111-7111-8111-111111111121';

  IF dependency_set_count <> 1 OR dependency_relation_count <> 1 THEN
    RAISE EXCEPTION
      'dependency decision evidence was not normalized completely: set %, relation %',
      dependency_set_count,
      dependency_relation_count;
  END IF;

  SELECT result.assessment_improvement_plan_id
    INTO replay_plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      source_projection_id,
      'stewardship_evidence',
      '0196f120-1111-7111-8111-111111111123',
      target_capability_id,
      accountable_organization_id,
      'close_stewardship_dependency_gap',
      'Close stewardship dependency gap',
      'stewardship_dependency_evidence',
      'Stewardship dependency evidence',
      '2027-01-31T00:00:00Z',
      'portfolio://fy2027/data-governance',
      ARRAY['0196f120-1111-7111-8111-111111111122'::uuid],
      ARRAY['0196f120-1111-7111-8111-111111111121'::uuid]
    ) AS result;

  IF replay_plan_id IS DISTINCT FROM inserted_plan_id THEN
    RAISE EXCEPTION 'exact dependency replay changed plan identity';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.create_data_management_improvement_plan(
        source_projection_id,
        'stewardship_evidence',
        '0196f120-1111-7111-8111-111111111123',
        target_capability_id,
        accountable_organization_id,
        'close_stewardship_dependency_gap',
        'Close stewardship dependency gap',
        'stewardship_dependency_evidence',
        'Stewardship dependency evidence',
        '2027-01-31T00:00:00Z',
        'portfolio://fy2027/data-governance',
        ARRAY[]::uuid[],
        ARRAY[]::uuid[]
      );
    RAISE EXCEPTION 'dependency-set drift was accepted for one decision id';
  EXCEPTION WHEN unique_violation OR check_violation THEN
    NULL;
  END;

  IF inserted_initiative_id = '0196f120-1111-7111-8111-111111111122'::uuid THEN
    RAISE EXCEPTION 'improvement initiative collapsed into its prerequisite';
  END IF;
END;
$$;

DO $$
DECLARE
  source_projection_id uuid;
  target_capability_id uuid;
  accountable_organization_id uuid;
BEGIN
  SELECT
      projection_record.data_management_assessment_projection_id,
      projection_record.subject_capability_object_id
    INTO source_projection_id, target_capability_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.superseded_at IS NULL
   ORDER BY projection_record.recorded_at DESC
   LIMIT 1;

  SELECT organization_record.architecture_object_id
    INTO accountable_organization_id
    FROM architecture_core.organization_unit AS organization_record
   WHERE organization_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   ORDER BY organization_record.architecture_object_id
   LIMIT 1;

  BEGIN
    PERFORM *
      FROM architecture_core.create_data_management_improvement_plan(
        source_projection_id,
        'stewardship_evidence',
        '0196f120-1111-7111-8111-111111111124',
        target_capability_id,
        accountable_organization_id,
        'reject_misaligned_dependency_arrays',
        'Reject misaligned dependency arrays',
        'dependency_array_guard',
        'Dependency array guard',
        '2027-02-28T00:00:00Z',
        NULL,
        ARRAY['0196f120-1111-7111-8111-111111111122'::uuid],
        ARRAY[]::uuid[]
      );
    RAISE EXCEPTION 'misaligned dependency and evidence arrays were accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
