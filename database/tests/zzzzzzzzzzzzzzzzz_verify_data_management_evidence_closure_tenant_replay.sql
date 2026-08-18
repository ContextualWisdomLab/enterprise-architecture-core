\set ON_ERROR_STOP on

-- Independent tenant/replay acceptance for the evidence-closure command.
-- Build a tenant_001 plan and accepted evidence inside this file so execution
-- does not depend on another database test's lexical filename ordering.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    event_source_uri,
    event_identifier,
    payload_sha256,
    schema_version,
    received_at,
    processed_at,
    processing_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f210-1111-7111-8111-111111111140',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f210-1111-7111-8111-111111111141',
    repeat('1', 64),
    '1.0.0',
    '2026-08-19T00:40:03Z',
    '2026-08-19T00:40:04Z',
    'processed'
);

DO $$
DECLARE
  projection_id uuid;
  plan_id uuid;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f210-1111-7111-8111-111111111140',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f210-1111-7111-8111-111111111142',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '2026-08-19T00:40:02Z',
      '2026-08-19T00:40:03Z',
      8000,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f210-1111-7111-8111-111111111143',
      repeat('2', 64),
      'https://example.com/evidence/tenant-replay-closure',
      NULL,
      ARRAY['control_evidence']::text[]
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'control_evidence',
      '0196f210-1111-7111-8111-111111111144',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap_tenant_replay',
      'Close control evidence gap for tenant replay acceptance',
      'control_evidence_accepted_tenant_replay',
      'Control evidence accepted for tenant replay acceptance',
      '2026-12-15T00:00:00Z',
      NULL
    ) AS result;

  IF plan_id IS NULL THEN
    RAISE EXCEPTION 'tenant/replay guard plan fixture was not created';
  END IF;
END;
$$;

INSERT INTO architecture_core.projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    event_source_uri,
    event_identifier,
    payload_sha256,
    schema_version,
    received_at,
    processed_at,
    processing_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f210-1111-7111-8111-111111111145',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f210-1111-7111-8111-111111111146',
    repeat('5', 64),
    '1.0.0',
    '2026-08-19T00:41:00Z',
    '2026-08-19T00:41:01Z',
    'processed'
);

DO $$
DECLARE
  plan_id uuid;
  acceptance_id uuid;
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
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f210-1111-7111-8111-111111111142'
     AND plan_record.missing_evidence_code = 'control_evidence';

  IF plan_id IS NULL THEN
    RAISE EXCEPTION 'tenant/replay guard fixture is unavailable';
  END IF;

  SELECT result.assessment_evidence_acceptance_id
    INTO acceptance_id
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f210-1111-7111-8111-111111111145',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f210-1111-7111-8111-111111111146',
      'observed',
      repeat('5', 64),
      '0196f210-1111-7111-8111-111111111151',
      '2026-08-19T00:41:02Z'
    ) AS result;

  IF acceptance_id IS NULL THEN
    RAISE EXCEPTION 'tenant/replay guard acceptance fixture was not created';
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
        '0196f210-1111-7111-8111-111111111145',
        'urn:cwl:tenant_002:data_context:assessment_evidence:0196f210-1111-7111-8111-111111111146',
        'observed',
        repeat('5', 64),
        '0196f210-1111-7111-8111-111111111152',
        '2026-08-19T00:41:03Z'
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
        '0196f210-1111-7111-8111-111111111145',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f210-1111-7111-8111-111111111146',
        'observed',
        repeat('6', 64),
        '0196f210-1111-7111-8111-111111111151',
        '2026-08-19T00:41:02Z'
      );
    RAISE EXCEPTION 'conflicting decision replay changed evidence digest';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;
