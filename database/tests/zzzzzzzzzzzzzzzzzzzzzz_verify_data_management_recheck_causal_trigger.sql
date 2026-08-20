\set ON_ERROR_STOP on

-- Reassessment must bind to the evidence acceptance that causally closed the
-- final projected gap, not to caller-supplied accepted_at ordering. This
-- realistic regression deliberately records the first gap with a later
-- accepted_at timestamp than the subsequently committed final-gap acceptance.

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
    '0196f400-1111-7111-8111-111111111180',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f400-1111-7111-8111-111111111181',
    repeat('a', 64),
    '1.0.0',
    '2026-08-19T01:00:00Z',
    '2026-08-19T01:00:01Z',
    'processed'
);

DO $$
DECLARE
  projection_id uuid;
  first_plan_id uuid;
  final_plan_id uuid;
  first_acceptance_id uuid;
  final_acceptance_id uuid;
  first_next_action text;
  final_next_action text;
  recheck_id uuid;
  recheck_outbox_id uuid;
  recheck_next_action text;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f400-1111-7111-8111-111111111180',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f400-1111-7111-8111-111111111182',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '2026-08-19T00:59:58Z',
      '2026-08-19T00:59:59Z',
      7200,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f400-1111-7111-8111-111111111183',
      repeat('b', 64),
      'https://example.com/evidence/recheck-causal-order',
      NULL,
      ARRAY['control_evidence', 'stewardship_evidence']::text[]
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO first_plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'control_evidence',
      '0196f400-1111-7111-8111-111111111184',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap_causal',
      'Close control evidence before causal recheck',
      'control_evidence_accepted_causal',
      'Control evidence accepted before final causal gap',
      '2026-12-31T00:00:00Z',
      NULL
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO final_plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'stewardship_evidence',
      '0196f400-1111-7111-8111-111111111185',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_stewardship_evidence_gap_causal',
      'Close stewardship evidence as final causal gap',
      'stewardship_evidence_accepted_causal',
      'Stewardship evidence accepted as final causal gap',
      '2026-12-31T00:00:00Z',
      NULL
    ) AS result;

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
  ) VALUES
  (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196f400-1111-7111-8111-111111111186',
      'urn:cwl:tenant_001:semantic_data_portal',
      '0196f400-1111-7111-8111-111111111187',
      repeat('c', 64),
      '1.0.0',
      '2026-08-19T01:00:02Z',
      '2026-08-19T01:00:03Z',
      'processed'
  ),
  (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196f400-1111-7111-8111-111111111188',
      'urn:cwl:tenant_001:semantic_data_portal',
      '0196f400-1111-7111-8111-111111111189',
      repeat('d', 64),
      '1.0.0',
      '2026-08-19T01:00:04Z',
      '2026-08-19T01:00:05Z',
      'processed'
  );

  SELECT
      result.assessment_evidence_acceptance_id,
      result.next_action
    INTO first_acceptance_id, first_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      first_plan_id,
      '0196f400-1111-7111-8111-111111111186',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f400-1111-7111-8111-111111111187',
      'observed',
      repeat('c', 64),
      '0196f400-1111-7111-8111-111111111190',
      '2026-08-19T01:00:10Z'
    ) AS result;

  SELECT
      result.assessment_evidence_acceptance_id,
      result.next_action
    INTO final_acceptance_id, final_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      final_plan_id,
      '0196f400-1111-7111-8111-111111111188',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f400-1111-7111-8111-111111111189',
      'observed',
      repeat('d', 64),
      '0196f400-1111-7111-8111-111111111191',
      '2026-08-19T01:00:09Z'
    ) AS result;

  IF first_next_action IS DISTINCT FROM 'close_remaining_assessment_gap'
     OR final_next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION
      'causal fixture did not establish first/final gap actions: %, %',
      first_next_action,
      final_next_action;
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.request_data_management_assessment_recheck(
        projection_id,
        first_acceptance_id,
        '0196f400-1111-7111-8111-111111111192',
        '2026-08-19T01:00:11Z'
      );
    RAISE EXCEPTION 'non-final evidence acceptance triggered reassessment';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM IS DISTINCT FROM
       'reassessment must bind to the evidence acceptance that closed the final gap' THEN
      RAISE;
    END IF;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.request_data_management_assessment_recheck(
        projection_id,
        final_acceptance_id,
        '0196f400-1111-7111-8111-111111111194',
        '2026-08-19T01:00:08Z'
      );
    RAISE EXCEPTION 'backdated reassessment request was accepted';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM IS DISTINCT FROM
       'assessment reassessment request cannot predate triggering evidence acceptance' THEN
      RAISE;
    END IF;
  END;

  SELECT
      result.assessment_recheck_request_id,
      result.outbox_event_id,
      result.next_action
    INTO recheck_id, recheck_outbox_id, recheck_next_action
    FROM architecture_core.request_data_management_assessment_recheck(
      projection_id,
      final_acceptance_id,
      '0196f400-1111-7111-8111-111111111193',
      '2026-08-19T01:00:11Z'
    ) AS result;

  IF recheck_id IS NULL
     OR recheck_outbox_id IS NULL
     OR recheck_next_action IS DISTINCT FROM 'await_assessment_recheck' THEN
    RAISE EXCEPTION
      'final causal evidence acceptance could not trigger reassessment: %, %, %',
      recheck_id,
      recheck_outbox_id,
      recheck_next_action;
  END IF;
END;
$$;
