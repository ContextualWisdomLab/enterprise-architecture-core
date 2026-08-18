\set ON_ERROR_STOP on

-- Security/truth regression for the data-management improvement boundary.
-- Projected evidence may be non-authoritative, but foreign-tenant provenance and
-- explicitly rejected/superseded source findings must never drive EA work.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111112',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111114',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '2026-09-18T00:00:00Z',
        '2026-09-18T00:00:01Z',
        7000,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_002:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111114',
        repeat('1', 64),
        NULL,
        NULL,
        ARRAY['foreign_provenance']::text[]
      );
    RAISE EXCEPTION 'cross-tenant assessment provenance was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
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
    '0196f100-1111-7111-8111-111111111115',
    'urn:cwl:tenant_001:semantic_data_portal',
    'data-management-assessment-rejected',
    repeat('2', 64),
    '1.0.0',
    '2026-10-18T00:00:02Z',
    '2026-10-18T00:00:03Z',
    'processed'
);

DO $$
DECLARE
  rejected_projection_id uuid;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO rejected_projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f100-1111-7111-8111-111111111115',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111115',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '2026-10-18T00:00:00Z',
      '2026-10-18T00:00:01Z',
      4000,
      'evidence_gap',
      'rejected',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111115',
      repeat('3', 64),
      NULL,
      NULL,
      ARRAY['rejected_finding']::text[]
    ) AS result;

  BEGIN
    PERFORM *
      FROM architecture_core.create_data_management_improvement_plan(
        rejected_projection_id,
        'rejected_finding',
        '0196f103-1111-7111-8111-111111111115',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '0196f100-1111-7111-8111-111111111110',
        'do_not_create_from_rejected',
        'Do not create from rejected evidence',
        'rejected_evidence_reviewed',
        'Rejected evidence reviewed',
        '2026-12-31T00:00:00Z',
        NULL
      );
    RAISE EXCEPTION 'rejected assessment finding created improvement work';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
