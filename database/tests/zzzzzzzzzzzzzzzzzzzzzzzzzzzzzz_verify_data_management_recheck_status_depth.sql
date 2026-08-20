\set ON_ERROR_STOP on

-- Reassessment status follows an append-only assessment succession chain, but
-- it must never become an unbounded graph traversal. This regression extends
-- the reviewed successor fixture beyond the supported depth inside a
-- subtransaction and requires the read to fail closed for the exact reason.

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
  current_result_uri text;
  next_result_id uuid;
  next_result_uri text;
  receipt_id uuid;
  event_id uuid;
  evidence_id uuid;
  child_count integer;
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

  current_result_uri :=
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f400-1111-7111-8111-111111111196';

  IF recheck_id IS NULL
     OR source_projection.data_management_assessment_projection_id IS NULL
     OR NOT EXISTS (
       SELECT 1
         FROM architecture_core.data_management_assessment_projection AS projection_record
        WHERE projection_record.tenant_record_id =
              '0195d145-64e8-7f4f-8a23-a0cc784cb711'
          AND projection_record.assessment_result_uri = current_result_uri
          AND projection_record.truth_status_code = 'observed'
          AND projection_record.superseded_at IS NULL
     ) THEN
    RAISE EXCEPTION 'reassessment depth fixture is unavailable';
  END IF;

  BEGIN
    -- Two successors already exist after the reassessment source. Append 31
    -- more so the source-to-terminal chain has 33 projections and must exceed
    -- the fixed 32-hop read bound.
    FOR chain_index IN 1..31 LOOP
      next_result_id := uuidv7();
      next_result_uri :=
          'urn:cwl:tenant_001:data_context:data_management_assessment:' ||
          next_result_id::text;
      receipt_id := uuidv7();
      event_id := uuidv7();
      evidence_id := uuidv7();

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
          receipt_id,
          'urn:cwl:tenant_001:semantic_data_portal',
          event_id,
          repeat('e', 64),
          '1.0.0',
          '2026-08-19T01:00:00Z',
          '2026-08-19T01:00:01Z',
          'processed'
      );

      PERFORM *
        FROM architecture_core.record_data_management_assessment_result(
          receipt_id,
          next_result_uri,
          'urn:cwl:tenant_001:ea_core:business_capability:' ||
              source_projection.subject_capability_object_id::text,
          source_projection.framework_code,
          source_projection.framework_version_label,
          source_projection.profile_code,
          source_projection.profile_version,
          '2026-08-19T00:59:58Z',
          '2026-08-19T00:59:59Z',
          10000,
          'evidence_complete',
          'observed',
          'urn:cwl:tenant_001:data_context:assessment_evidence:' ||
              evidence_id::text,
          repeat('f', 64),
          'https://example.com/evidence/recheck-depth-bound',
          current_result_uri,
          ARRAY[]::text[]
        );

      current_result_uri := next_result_uri;
    END LOOP;

    PERFORM *
      FROM architecture_core.read_data_management_assessment_recheck_status(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        recheck_id
      );

    RAISE EXCEPTION 'reassessment status traversed beyond its fixed depth bound';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM IS DISTINCT FROM
       'assessment reassessment successor chain exceeds supported depth' THEN
      RAISE;
    END IF;
  END;

  -- Catching the expected exception rolls the nested subtransaction back. The
  -- reviewed successor from the preceding status test must therefore remain
  -- terminal and no synthetic depth fixture may leak into cumulative tests.
  SELECT count(*)
    INTO child_count
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.supersedes_assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f400-1111-7111-8111-111111111196';

  IF child_count <> 0 THEN
    RAISE EXCEPTION 'reassessment depth regression leaked synthetic successors';
  END IF;
END;
$$;
