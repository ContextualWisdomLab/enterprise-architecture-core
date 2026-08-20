\set ON_ERROR_STOP on

-- Executable buyer acceptance for following an accepted reassessment request.
-- The first candidate intentionally fails when the status query is not wired to
-- the normalized missing-evidence projection owned by this database.

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
  successor_projection_id uuid;
  status_record record;
BEGIN
  SELECT
      request_record.assessment_recheck_request_id,
      projection_record.*
    INTO recheck_id, source_projection
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
    RAISE EXCEPTION 'reassessment status source fixture is unavailable';
  END IF;

  SELECT *
    INTO status_record
    FROM architecture_core.read_data_management_assessment_recheck_status(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      recheck_id
    );

  IF status_record.assessment_recheck_request_id IS DISTINCT FROM recheck_id
     OR status_record.successor_assessment_projection_id IS NOT NULL
     OR status_record.recheck_state_code IS DISTINCT FROM 'awaiting_result'
     OR status_record.successor_readiness_code IS NOT NULL
     OR status_record.successor_overall_score_basis_points IS NOT NULL
     OR status_record.successor_missing_evidence_count IS NOT NULL
     OR status_record.next_action IS DISTINCT FROM 'await_assessment_recheck' THEN
    RAISE EXCEPTION 'waiting reassessment status is not buyer-actionable';
  END IF;

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
      '0196f400-1111-7111-8111-111111111190',
      'urn:cwl:tenant_001:semantic_data_portal',
      '0196f400-1111-7111-8111-111111111191',
      repeat('a', 64),
      '1.0.0',
      '2026-08-19T00:40:00Z',
      '2026-08-19T00:40:01Z',
      'processed'
  );

  SELECT result.data_management_assessment_projection_id
    INTO successor_projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f400-1111-7111-8111-111111111190',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f400-1111-7111-8111-111111111192',
      'urn:cwl:tenant_001:ea_core:business_capability:' ||
          source_projection.subject_capability_object_id::text,
      source_projection.framework_code,
      source_projection.framework_version_label,
      source_projection.profile_code,
      '2026-08-19T00:39:58Z',
      '2026-08-19T00:39:59Z',
      8200,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f400-1111-7111-8111-111111111193',
      repeat('b', 64),
      'https://example.com/evidence/recheck-successor',
      source_projection.assessment_result_uri,
      ARRAY['stewardship_evidence']::text[]
    ) AS result;

  SELECT *
    INTO status_record
    FROM architecture_core.read_data_management_assessment_recheck_status(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      recheck_id
    );

  IF status_record.assessment_recheck_request_id IS DISTINCT FROM recheck_id
     OR status_record.data_management_assessment_projection_id IS DISTINCT FROM
        source_projection.data_management_assessment_projection_id
     OR status_record.successor_assessment_projection_id IS DISTINCT FROM
        successor_projection_id
     OR status_record.recheck_state_code IS DISTINCT FROM 'evidence_gap'
     OR status_record.successor_readiness_code IS DISTINCT FROM 'evidence_gap'
     OR status_record.successor_overall_score_basis_points IS DISTINCT FROM 8200
     OR status_record.successor_missing_evidence_count IS DISTINCT FROM 1
     OR status_record.next_action IS DISTINCT FROM
        'plan_remaining_assessment_gap' THEN
    RAISE EXCEPTION 'successor reassessment status lost evidence or next action';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.read_data_management_assessment_recheck_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        recheck_id
      );
    RAISE EXCEPTION 'cross-tenant reassessment status was disclosed';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
