\set ON_ERROR_STOP on

-- RED acceptance for the versioned Context Graph assessment boundary. Historical
-- assessment scores must retain the exact CWL-authored profile version rather
-- than resolving a reused profile code to whichever definition is current later.

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
    '0196f100-1111-7111-8111-111111111130',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f100-1111-7111-8111-111111111131',
    repeat('9', 64),
    '1.0.0',
    '2026-10-20T00:00:02Z',
    '2026-10-20T00:00:03Z',
    'processed'
)
ON CONFLICT DO NOTHING;

DO $$
DECLARE
  inserted_projection_id uuid;
  replay_projection_id uuid;
  stored_profile_version text;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO inserted_projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f100-1111-7111-8111-111111111130',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111130',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.2.3',
      '2026-10-20T00:00:00Z',
      '2026-10-20T00:00:01Z',
      7300,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111130',
      repeat('8', 64),
      NULL,
      NULL,
      ARRAY['profile_version_evidence']::text[]
    ) AS result;

  SELECT projection.profile_version
    INTO stored_profile_version
    FROM architecture_core.data_management_assessment_projection AS projection
   WHERE projection.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection.data_management_assessment_projection_id =
         inserted_projection_id;

  IF stored_profile_version IS DISTINCT FROM '1.2.3' THEN
    RAISE EXCEPTION
      'assessment profile version was not preserved exactly: %',
      stored_profile_version;
  END IF;

  SELECT result.data_management_assessment_projection_id
    INTO replay_projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f100-1111-7111-8111-111111111130',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111130',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.2.3',
      '2026-10-20T00:00:00Z',
      '2026-10-20T00:00:01Z',
      7300,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111130',
      repeat('8', 64),
      NULL,
      NULL,
      ARRAY['profile_version_evidence']::text[]
    ) AS result;

  IF replay_projection_id IS DISTINCT FROM inserted_projection_id THEN
    RAISE EXCEPTION 'exact profile-version replay changed projection identity';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111130',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111130',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '1.2.4',
        '2026-10-20T00:00:00Z',
        '2026-10-20T00:00:01Z',
        7300,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111130',
        repeat('8', 64),
        NULL,
        NULL,
        ARRAY['profile_version_evidence']::text[]
      );
    RAISE EXCEPTION 'profile-version drift was accepted for an existing result id';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111130',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111132',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        'latest',
        '2026-10-20T00:00:00Z',
        '2026-10-20T00:00:01Z',
        7300,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111132',
        repeat('7', 64),
        NULL,
        NULL,
        ARRAY['profile_version_evidence']::text[]
      );
    RAISE EXCEPTION 'non-semver assessment profile version was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111130',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111133',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '2026-10-20T00:00:00Z',
        '2026-10-20T00:00:01Z',
        7300,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111133',
        repeat('6', 64),
        NULL,
        NULL,
        ARRAY['profile_version_evidence']::text[]
      );
    RAISE EXCEPTION 'assessment profile version omission was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
