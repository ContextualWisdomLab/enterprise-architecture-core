\set ON_ERROR_STOP on

-- Buyer acceptance for closing an assessment gap only after Semantic Data Portal
-- evidence with an acceptable truth status is received. This test intentionally
-- precedes migration 0036 so the first candidate is RED at the missing command.

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
    '0196f200-1111-7111-8111-111111111140',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f200-1111-7111-8111-111111111141',
    repeat('1', 64),
    '1.0.0',
    '2026-08-19T00:00:03Z',
    '2026-08-19T00:00:04Z',
    'processed'
);

DO $$
DECLARE
  projection_id uuid;
  plan_id uuid;
  initiative_id uuid;
  milestone_id uuid;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f200-1111-7111-8111-111111111140',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '2026-08-19T00:00:02Z',
      '2026-08-19T00:00:03Z',
      8100,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111143',
      repeat('2', 64),
      'https://example.com/evidence/assessment-closure',
      NULL,
      ARRAY['control_evidence']::text[]
    ) AS result;

  SELECT
      result.assessment_improvement_plan_id,
      result.remediation_initiative_id,
      result.initiative_milestone_id
    INTO plan_id, initiative_id, milestone_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'control_evidence',
      '0196f200-1111-7111-8111-111111111144',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap_2',
      'Close control evidence gap for closure acceptance',
      'control_evidence_accepted_2',
      'Control evidence accepted for closure',
      '2026-11-30T00:00:00Z',
      'portfolio://fy2026/data-governance'
    ) AS result;

  IF plan_id IS NULL OR initiative_id IS NULL OR milestone_id IS NULL THEN
    RAISE EXCEPTION 'closure fixture did not create complete improvement work';
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
) VALUES
(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f200-1111-7111-8111-111111111145',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f200-1111-7111-8111-111111111146',
    repeat('5', 64),
    '1.0.0',
    '2026-08-19T00:10:00Z',
    '2026-08-19T00:10:01Z',
    'processed'
),
(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f200-1111-7111-8111-111111111147',
    'urn:cwl:tenant_001:pg_erd_cloud',
    '0196f200-1111-7111-8111-111111111148',
    repeat('4', 64),
    '1.0.0',
    '2026-08-19T00:10:00Z',
    '2026-08-19T00:10:01Z',
    'processed'
);

DO $$
DECLARE
  plan_id uuid;
  milestone_id uuid;
  acceptance_id uuid;
  completion_id uuid;
  evidence_event_id uuid;
  milestone_event_id uuid;
  replay_acceptance_id uuid;
  replay_completion_id uuid;
  replay_evidence_event_id uuid;
  replay_milestone_event_id uuid;
  next_action text;
  replay_next_action text;
  acceptance_count integer;
  completion_count integer;
  event_count integer;
BEGIN
  SELECT
      plan_record.assessment_improvement_plan_id,
      plan_record.initiative_milestone_id
    INTO plan_id, milestone_id
    FROM architecture_core.assessment_improvement_plan AS plan_record
    JOIN architecture_core.data_management_assessment_projection AS projection_record
      ON projection_record.tenant_record_id = plan_record.tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         plan_record.data_management_assessment_projection_id
   WHERE plan_record.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142'
     AND plan_record.missing_evidence_code = 'control_evidence';

  IF plan_id IS NULL OR milestone_id IS NULL THEN
    RAISE EXCEPTION 'closure plan fixture is unavailable';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111145',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146',
        'inferred',
        repeat('5', 64),
        '0196f200-1111-7111-8111-111111111149',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'inferred assessment evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111147',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111148',
        'observed',
        repeat('4', 64),
        '0196f200-1111-7111-8111-111111111150',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'foreign-authority assessment evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111145',
        'urn:cwl:tenant_001:data_context:assessment_evidence:not-a-uuid',
        'observed',
        repeat('5', 64),
        '0196f200-1111-7111-8111-111111111153',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'malformed evidence URI was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111145',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146',
        'observed',
        repeat('6', 64),
        '0196f200-1111-7111-8111-111111111152',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'evidence digest not bound to projection receipt payload';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT
      result.assessment_evidence_acceptance_id,
      result.milestone_completion_record_id,
      result.evidence_outbox_event_id,
      result.milestone_outbox_event_id,
      result.next_action
    INTO
      acceptance_id,
      completion_id,
      evidence_event_id,
      milestone_event_id,
      next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f200-1111-7111-8111-111111111145',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146',
      'observed',
      repeat('5', 64),
      '0196f200-1111-7111-8111-111111111151',
      '2026-08-19T00:10:02Z'
    ) AS result;

  IF acceptance_id IS NULL
     OR completion_id IS NULL
     OR evidence_event_id IS NULL
     OR milestone_event_id IS NULL
     OR next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION
      'evidence closure did not return complete buyer receipt: %, %, %, %, %',
      acceptance_id,
      completion_id,
      evidence_event_id,
      milestone_event_id,
      next_action;
  END IF;

  SELECT count(*)
    INTO acceptance_count
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
   WHERE acceptance_record.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND acceptance_record.assessment_evidence_acceptance_id = acceptance_id
     AND acceptance_record.assessment_improvement_plan_id = plan_id
     AND acceptance_record.projection_receipt_id = '0196f200-1111-7111-8111-111111111145'
     AND acceptance_record.evidence_uri =
         'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146'
     AND acceptance_record.evidence_truth_status_code = 'observed'
     AND acceptance_record.evidence_sha256 = repeat('5', 64)
     AND acceptance_record.accepted_at = '2026-08-19T00:10:02Z';

  IF acceptance_count <> 1 THEN
    RAISE EXCEPTION 'accepted evidence provenance was not preserved';
  END IF;

  SELECT count(*)
    INTO completion_count
    FROM architecture_core.milestone_completion_record AS completion_record
   WHERE completion_record.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND completion_record.milestone_completion_record_id = completion_id
     AND completion_record.initiative_milestone_id = milestone_id
     AND completion_record.assessment_evidence_acceptance_id = acceptance_id
     AND completion_record.completed_at = '2026-08-19T00:10:02Z';

  IF completion_count <> 1 THEN
    RAISE EXCEPTION 'milestone completion was not bound to accepted evidence';
  END IF;

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND (
       (
         event_record.outbox_event_id = evidence_event_id
         AND event_record.event_type_code =
             'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1'
         AND event_record.decision_request_id = '0196f200-1111-7111-8111-111111111151'
         AND event_record.event_payload_json ->> 'evidence_uri' =
             'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146'
         AND event_record.event_payload_json ->> 'evidence_truth_status_code' = 'observed'
       )
       OR (
         event_record.outbox_event_id = milestone_event_id
         AND event_record.event_type_code =
             'org.contextualwisdomlab.ea.data_management.milestone_completed.v1'
         AND event_record.decision_request_id IS NULL
         AND event_record.causation_event_id = evidence_event_id
         AND event_record.event_payload_json ->> 'initiative_milestone_id' = milestone_id::text
       )
     )
     AND NOT (event_record.event_payload_json ? 'provenance_source_locator')
     AND NOT (event_record.event_payload_json ? 'funding_reference');

  IF event_count <> 2 THEN
    RAISE EXCEPTION 'evidence/milestone outbox evidence is incomplete or overexposed: %', event_count;
  END IF;

  SELECT
      result.assessment_evidence_acceptance_id,
      result.milestone_completion_record_id,
      result.evidence_outbox_event_id,
      result.milestone_outbox_event_id,
      result.next_action
    INTO
      replay_acceptance_id,
      replay_completion_id,
      replay_evidence_event_id,
      replay_milestone_event_id,
      replay_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f200-1111-7111-8111-111111111145',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111146',
      'observed',
      repeat('5', 64),
      '0196f200-1111-7111-8111-111111111151',
      '2026-08-19T00:10:02Z'
    ) AS result;

  IF replay_acceptance_id IS DISTINCT FROM acceptance_id
     OR replay_completion_id IS DISTINCT FROM completion_id
     OR replay_evidence_event_id IS DISTINCT FROM evidence_event_id
     OR replay_milestone_event_id IS DISTINCT FROM milestone_event_id
     OR replay_next_action IS DISTINCT FROM next_action THEN
    RAISE EXCEPTION 'exact evidence-closure replay changed its receipt';
  END IF;

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.outbox_event_id IN (evidence_event_id, milestone_event_id);

  IF event_count <> 2 THEN
    RAISE EXCEPTION 'exact evidence-closure replay duplicated outbox evidence';
  END IF;
END;
$$;
