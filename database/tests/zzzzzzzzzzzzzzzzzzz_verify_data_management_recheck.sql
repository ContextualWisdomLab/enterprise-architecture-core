\set ON_ERROR_STOP on

-- Buyer acceptance for making the evidence-closure next action executable.
-- This file intentionally lands before the recheck migration so the first
-- candidate fails at the missing command boundary.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- A partially closed assessment must not be sent for recheck.
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
    '0196f300-1111-7111-8111-111111111160',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f300-1111-7111-8111-111111111161',
    repeat('7', 64),
    '1.0.0',
    '2026-08-19T00:20:00Z',
    '2026-08-19T00:20:01Z',
    'processed'
);

DO $$
DECLARE
  projection_id uuid;
  plan_id uuid;
  acceptance_id uuid;
  closure_next_action text;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f300-1111-7111-8111-111111111160',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f300-1111-7111-8111-111111111162',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.0.0',
      '2026-08-19T00:19:58Z',
      '2026-08-19T00:19:59Z',
      7000,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f300-1111-7111-8111-111111111163',
      repeat('8', 64),
      'https://example.com/evidence/recheck-partial-assessment',
      NULL,
      ARRAY['control_evidence', 'stewardship_evidence']::text[]
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'control_evidence',
      '0196f300-1111-7111-8111-111111111164',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap_3',
      'Close first gap before reassessment',
      'control_evidence_accepted_3',
      'First gap evidence accepted',
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
  ) VALUES (
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196f300-1111-7111-8111-111111111165',
      'urn:cwl:tenant_001:semantic_data_portal',
      '0196f300-1111-7111-8111-111111111166',
      repeat('9', 64),
      '1.0.0',
      '2026-08-19T00:20:02Z',
      '2026-08-19T00:20:03Z',
      'processed'
  );

  SELECT
      result.assessment_evidence_acceptance_id,
      result.next_action
    INTO acceptance_id, closure_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f300-1111-7111-8111-111111111165',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f300-1111-7111-8111-111111111166',
      'observed',
      repeat('9', 64),
      '0196f300-1111-7111-8111-111111111167',
      '2026-08-19T00:20:04Z'
    ) AS result;

  IF acceptance_id IS NULL
     OR closure_next_action IS DISTINCT FROM 'close_remaining_assessment_gap' THEN
    RAISE EXCEPTION
      'partial closure fixture did not expose remaining-gap action: %, %',
      acceptance_id,
      closure_next_action;
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.request_data_management_assessment_recheck(
        projection_id,
        acceptance_id,
        '0196f300-1111-7111-8111-111111111168',
        '2026-08-19T00:20:05Z'
      );
    RAISE EXCEPTION 'partially closed assessment was sent for reassessment';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

-- The one-gap closure fixture from the preceding acceptance now has no
-- remaining unaccepted gap and may emit exactly one reassessment request.
DO $$
DECLARE
  projection_id uuid;
  acceptance_id uuid;
  trigger_causation_event_id uuid;
  recheck_id uuid;
  outbox_id uuid;
  replay_recheck_id uuid;
  replay_outbox_id uuid;
  next_action text;
  replay_next_action text;
  record_count integer;
  event_count integer;
BEGIN
  SELECT projection_record.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142'
     AND projection_record.superseded_at IS NULL;

  SELECT acceptance_record.assessment_evidence_acceptance_id
    INTO acceptance_id
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
    JOIN architecture_core.assessment_improvement_plan AS plan_record
      ON plan_record.tenant_record_id = acceptance_record.tenant_record_id
     AND plan_record.assessment_improvement_plan_id =
         acceptance_record.assessment_improvement_plan_id
   WHERE acceptance_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND plan_record.data_management_assessment_projection_id = projection_id;

  IF projection_id IS NULL OR acceptance_id IS NULL THEN
    RAISE EXCEPTION 'completed reassessment fixture is unavailable';
  END IF;

  SELECT event_record.outbox_event_id
    INTO trigger_causation_event_id
    FROM architecture_core.outbox_event AS event_record
    JOIN architecture_core.assessment_evidence_acceptance AS acceptance_record
      ON acceptance_record.tenant_record_id = event_record.tenant_record_id
     AND acceptance_record.decision_request_id = event_record.decision_request_id
   WHERE acceptance_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND acceptance_record.assessment_evidence_acceptance_id = acceptance_id
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1';

  IF trigger_causation_event_id IS NULL THEN
    RAISE EXCEPTION 'completed reassessment fixture lacks causal acceptance event';
  END IF;

  SELECT
      result.assessment_recheck_request_id,
      result.outbox_event_id,
      result.next_action
    INTO recheck_id, outbox_id, next_action
    FROM architecture_core.request_data_management_assessment_recheck(
      projection_id,
      acceptance_id,
      '0196f300-1111-7111-8111-111111111169',
      '2026-08-19T00:30:00Z'
    ) AS result;

  IF recheck_id IS NULL
     OR outbox_id IS NULL
     OR next_action IS DISTINCT FROM 'await_assessment_recheck' THEN
    RAISE EXCEPTION
      'reassessment request did not return complete buyer receipt: %, %, %',
      recheck_id,
      outbox_id,
      next_action;
  END IF;

  SELECT count(*)
    INTO record_count
    FROM architecture_core.assessment_recheck_request AS recheck_record
   WHERE recheck_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND recheck_record.assessment_recheck_request_id = recheck_id
     AND recheck_record.data_management_assessment_projection_id = projection_id
     AND recheck_record.trigger_evidence_acceptance_id = acceptance_id
     AND recheck_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111169'
     AND recheck_record.requested_at = '2026-08-19T00:30:00Z';

  IF record_count <> 1 THEN
    RAISE EXCEPTION 'immutable reassessment request evidence is incomplete';
  END IF;

  BEGIN
    UPDATE architecture_core.assessment_recheck_request
       SET requested_at = '2026-08-19T00:30:01Z'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND assessment_recheck_request_id = recheck_id;
    RAISE EXCEPTION 'reassessment request evidence was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    DELETE FROM architecture_core.assessment_recheck_request
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND assessment_recheck_request_id = recheck_id;
    RAISE EXCEPTION 'reassessment request evidence was hard-deletable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.outbox_event_id = outbox_id
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.assessment_recheck_requested.v1'
     AND event_record.causation_event_id = trigger_causation_event_id
     AND event_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111169'
     AND event_record.event_payload_json ->> 'assessment_recheck_request_id' =
         recheck_id::text
     AND event_record.event_payload_json ->> 'data_management_assessment_projection_id' =
         projection_id::text
     AND event_record.event_payload_json ->> 'trigger_evidence_acceptance_id' =
         acceptance_id::text
     AND event_record.event_payload_json ->> 'assessment_result_uri' =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142'
     AND event_record.event_payload_json ->> 'next_action' = 'await_assessment_recheck'
     AND NOT (event_record.event_payload_json ? 'provenance_source_locator')
     AND NOT (event_record.event_payload_json ? 'funding_reference');

  IF event_count <> 1 THEN
    RAISE EXCEPTION 'privacy-minimized reassessment outbox evidence is missing';
  END IF;

  SELECT
      result.assessment_recheck_request_id,
      result.outbox_event_id,
      result.next_action
    INTO replay_recheck_id, replay_outbox_id, replay_next_action
    FROM architecture_core.request_data_management_assessment_recheck(
      projection_id,
      acceptance_id,
      '0196f300-1111-7111-8111-111111111169',
      '2026-08-19T00:30:00Z'
    ) AS result;

  IF replay_recheck_id IS DISTINCT FROM recheck_id
     OR replay_outbox_id IS DISTINCT FROM outbox_id
     OR replay_next_action IS DISTINCT FROM next_action THEN
    RAISE EXCEPTION 'exact reassessment replay changed its receipt';
  END IF;

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.assessment_recheck_requested.v1'
     AND event_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111169';

  IF event_count <> 1 THEN
    RAISE EXCEPTION 'exact reassessment replay duplicated outbox evidence';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.request_data_management_assessment_recheck(
        projection_id,
        acceptance_id,
        '0196f300-1111-7111-8111-111111111169',
        '2026-08-19T00:30:01Z'
      );
    RAISE EXCEPTION 'conflicting reassessment decision replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;

  PERFORM set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb712',
    false
  );
  BEGIN
    PERFORM *
      FROM architecture_core.request_data_management_assessment_recheck(
        projection_id,
        acceptance_id,
        '0196f300-1111-7111-8111-111111111170',
        '2026-08-19T00:30:01Z'
      );
    RAISE EXCEPTION 'cross-tenant reassessment request was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  PERFORM set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
  );
END;
$$;
