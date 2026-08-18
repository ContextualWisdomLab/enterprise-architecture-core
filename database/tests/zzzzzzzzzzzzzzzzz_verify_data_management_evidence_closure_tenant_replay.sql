\set ON_ERROR_STOP on

-- Strengthen the evidence-closure command boundary before production code exists.
-- The prior buyer acceptance establishes tenant_001's plan/evidence. This file
-- proves tenant context cannot cross that boundary and a UUIDv7 decision replay
-- cannot silently change accepted evidence meaning.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  plan_id uuid;
BEGIN
  SELECT plan_record.assessment_improvement_plan_id
    INTO plan_id
    FROM architecture_core.assessment_improvement_plan AS plan_record
    JOIN architecture_core.data_management_assessment_projection AS projection_record
      ON projection_record.tenant_record_id = plan_record.tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         plan_record.data_management_assessment_projection_id
   WHERE plan_record.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142'
     AND plan_record.missing_evidence_code = 'control_evidence';

  IF plan_id IS NULL THEN
    RAISE EXCEPTION 'tenant/replay guard fixture is unavailable';
  END IF;

  PERFORM set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb712',
    false
  );
  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111145',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146',
        'observed',
        repeat('5', 64),
        '0196f200-1111-7111-8111-111111111152',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'cross-tenant evidence closure was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  PERFORM set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
  );
  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111145',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146',
        'observed',
        repeat('6', 64),
        '0196f200-1111-7111-8111-111111111151',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'conflicting decision replay changed evidence digest';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;
