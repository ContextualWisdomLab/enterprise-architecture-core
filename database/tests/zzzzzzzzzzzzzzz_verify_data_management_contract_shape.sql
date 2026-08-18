\set ON_ERROR_STOP on

-- Contract-shape regression for the Context Graph data-management assessment
-- boundary. `missing_evidence_codes` is a required bounded unique array of
-- canonical code strings; the EA projection must fail closed rather than trim,
-- deduplicate, or treat a missing array as an empty one.

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
    '0196f100-1111-7111-8111-111111111116',
    'urn:cwl:tenant_001:semantic_data_portal',
    'data-management-assessment-contract-shape',
    repeat('4', 64),
    '1.0.0',
    '2026-10-19T00:00:02Z',
    '2026-10-19T00:00:03Z',
    'processed'
);

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111116',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111116',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '2026-10-19T00:00:00Z',
        '2026-10-19T00:00:01Z',
        9000,
        'evidence_complete',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111116',
        repeat('5', 64),
        NULL,
        NULL,
        NULL::text[]
      );
    RAISE EXCEPTION 'NULL missing_evidence_codes was accepted';
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
        '0196f100-1111-7111-8111-111111111116',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111117',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '2026-10-19T00:00:00Z',
        '2026-10-19T00:00:01Z',
        7000,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111117',
        repeat('6', 64),
        NULL,
        NULL,
        ARRAY[' control_evidence ']::text[]
      );
    RAISE EXCEPTION 'whitespace-normalized missing evidence code was accepted';
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
        '0196f100-1111-7111-8111-111111111116',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111118',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '2026-10-19T00:00:00Z',
        '2026-10-19T00:00:01Z',
        7000,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111118',
        repeat('7', 64),
        NULL,
        NULL,
        ARRAY['control_evidence', 'control_evidence']::text[]
      );
    RAISE EXCEPTION 'duplicate missing evidence codes were silently deduplicated';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
DECLARE
  oversized_codes text[];
BEGIN
  SELECT array_agg('gap_' || lpad(code_number::text, 3, '0') ORDER BY code_number)
    INTO oversized_codes
    FROM generate_series(1, 257) AS code_number;

  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111116',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111119',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '2026-10-19T00:00:00Z',
        '2026-10-19T00:00:01Z',
        7000,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111119',
        repeat('8', 64),
        NULL,
        NULL,
        oversized_codes
      );
    RAISE EXCEPTION 'more than 256 missing evidence codes were accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;