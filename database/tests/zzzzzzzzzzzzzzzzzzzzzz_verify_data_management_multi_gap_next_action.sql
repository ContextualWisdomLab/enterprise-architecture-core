\set ON_ERROR_STOP on

-- Regression acceptance for a multi-gap assessment. Closing one accepted gap
-- must keep the buyer on evidence collection; closing the final gap may request
-- a reassessment. This exercises both next-action branches deterministically.

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
    '0196f700-1111-7111-8111-111111111300',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f700-1111-7111-8111-111111111301',
    repeat('a', 64),
    '1.0.0',
    '2026-08-19T02:00:00Z',
    '2026-08-19T02:00:01Z',
    'processed'
);

CREATE TEMP TABLE data_management_multi_gap_fixture (
    assessment_projection_id uuid NOT NULL,
    first_plan_id uuid NOT NULL,
    second_plan_id uuid NOT NULL
);

DO $$
DECLARE
  projection_id uuid;
  first_plan_id uuid;
  second_plan_id uuid;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f700-1111-7111-8111-111111111300',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f700-1111-7111-8111-111111111302',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.0.0',
      '2026-08-19T01:59:58Z',
      '2026-08-19T01:59:59Z',
      6500,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f700-1111-7111-8111-111111111303',
      repeat('b', 64),
      'https://example.com/evidence/multi-gap-assessment',
      NULL,
      ARRAY['policy_evidence', 'quality_evidence']::text[]
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO first_plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'policy_evidence',
      '0196f700-1111-7111-8111-111111111304',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_policy_evidence_gap',
      'Close policy evidence gap',
      'policy_evidence_accepted',
      'Policy evidence accepted',
      '2026-12-31T00:00:00Z',
      NULL
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO second_plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'quality_evidence',
      '0196f700-1111-7111-8111-111111111305',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_quality_evidence_gap',
      'Close quality evidence gap',
      'quality_evidence_accepted',
      'Quality evidence accepted',
      '2026-12-31T00:00:00Z',
      NULL
    ) AS result;

  IF projection_id IS NULL OR first_plan_id IS NULL OR second_plan_id IS NULL THEN
    RAISE EXCEPTION 'multi-gap fixture did not create both improvement plans';
  END IF;

  INSERT INTO data_management_multi_gap_fixture (
      assessment_projection_id,
      first_plan_id,
      second_plan_id
  ) VALUES (projection_id, first_plan_id, second_plan_id);
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
) VALUES
(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f700-1111-7111-8111-111111111306',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f700-1111-7111-8111-111111111307',
    repeat('c', 64),
    '1.0.0',
    '2026-08-19T02:00:02Z',
    '2026-08-19T02:00:03Z',
    'processed'
),
(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f700-1111-7111-8111-111111111308',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f700-1111-7111-8111-111111111309',
    repeat('d', 64),
    '1.0.0',
    '2026-08-19T02:00:04Z',
    '2026-08-19T02:00:05Z',
    'processed'
);

DO $$
DECLARE
  first_plan_id uuid;
  second_plan_id uuid;
  first_next_action text;
  second_next_action text;
  acceptance_count integer;
BEGIN
  SELECT fixture.first_plan_id, fixture.second_plan_id
    INTO first_plan_id, second_plan_id
    FROM data_management_multi_gap_fixture AS fixture;

  SELECT result.next_action
    INTO first_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      first_plan_id,
      '0196f700-1111-7111-8111-111111111306',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f700-1111-7111-8111-111111111307',
      'observed',
      repeat('c', 64),
      '0196f700-1111-7111-8111-111111111310',
      '2026-08-19T02:00:06Z'
    ) AS result;

  IF first_next_action IS DISTINCT FROM 'close_remaining_assessment_gap' THEN
    RAISE EXCEPTION
      'first of two evidence gaps returned wrong next action: %',
      first_next_action;
  END IF;

  SELECT result.next_action
    INTO second_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      second_plan_id,
      '0196f700-1111-7111-8111-111111111308',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f700-1111-7111-8111-111111111309',
      'observed',
      repeat('d', 64),
      '0196f700-1111-7111-8111-111111111311',
      '2026-08-19T02:00:07Z'
    ) AS result;

  IF second_next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION
      'final evidence gap returned wrong next action: %',
      second_next_action;
  END IF;

  SELECT count(*)
    INTO acceptance_count
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
   WHERE acceptance_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND acceptance_record.decision_request_id IN (
         '0196f700-1111-7111-8111-111111111310',
         '0196f700-1111-7111-8111-111111111311'
     );

  IF acceptance_count <> 2 THEN
    RAISE EXCEPTION 'multi-gap acceptance did not persist both decisions';
  END IF;
END;
$$;
