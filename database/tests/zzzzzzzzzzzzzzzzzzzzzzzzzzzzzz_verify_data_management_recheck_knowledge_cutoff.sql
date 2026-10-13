\set ON_ERROR_STOP on

-- A reassessment result must have evaluated knowledge at or after the governed
-- recheck request. A late-arriving projection with a newer system receipt but
-- a pre-request knowledge cutoff is stale evidence and must fail closed rather
-- than advancing the buyer's remediation loop.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  recheck_id uuid;
  source_projection architecture_core.data_management_assessment_projection%ROWTYPE;
  remaining_successors integer;
BEGIN
  SELECT request_record.assessment_recheck_request_id
    INTO recheck_id
    FROM architecture_core.assessment_recheck_request AS request_record
   WHERE request_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND request_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111169';

  SELECT projection_record.*
    INTO source_projection
    FROM architecture_core.assessment_recheck_request AS request_record
    JOIN architecture_core.data_management_assessment_projection AS projection_record
      ON projection_record.tenant_record_id = request_record.tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         request_record.data_management_assessment_projection_id
   WHERE request_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND request_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111169';

  IF recheck_id IS NULL
     OR source_projection.data_management_assessment_projection_id IS NULL THEN
    RAISE EXCEPTION 'reassessment knowledge-cutoff fixture is unavailable';
  END IF;

  BEGIN
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
        '0196f400-1111-7111-8111-111111111198',
        'urn:cwl:tenant_001:semantic_data_portal',
        '0196f400-1111-7111-8111-111111111199',
        repeat('c', 64),
        '1.0.0',
        '2026-08-19T00:40:00Z',
        '2026-08-19T00:40:01Z',
        'processed'
    );

    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f400-1111-7111-8111-111111111198',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f400-1111-7111-8111-111111111200',
        'urn:cwl:tenant_001:ea_core:business_capability:' ||
            source_projection.subject_capability_object_id::text,
        source_projection.framework_code,
        source_projection.framework_version_label,
        source_projection.profile_code,
        source_projection.profile_version,
        '2026-08-19T00:29:59Z',
        '2026-08-19T00:39:59Z',
        10000,
        'evidence_complete',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f400-1111-7111-8111-111111111201',
        repeat('d', 64),
        'https://example.com/evidence/stale-recheck-successor',
        source_projection.assessment_result_uri,
        ARRAY[]::text[]
      );

    PERFORM *
      FROM architecture_core.read_data_management_assessment_recheck_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        recheck_id
      );

    RAISE EXCEPTION
      'reassessment status accepted successor knowledge predating its request';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*)
    INTO remaining_successors
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.supersedes_assessment_result_uri =
         source_projection.assessment_result_uri;

  IF remaining_successors <> 0 THEN
    RAISE EXCEPTION
      'stale reassessment regression fixture leaked projection state';
  END IF;
END;
$$;
