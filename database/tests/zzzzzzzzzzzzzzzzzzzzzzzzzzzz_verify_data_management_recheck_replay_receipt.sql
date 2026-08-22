\set ON_ERROR_STOP on

-- RED acceptance: an exact reassessment retry must expose replay evidence through
-- the same purpose-bound tenant runtime port used by the HTTP adapter. The
-- durable fixture was created by the earlier reassessment acceptance test.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  projection_id uuid;
  acceptance_id uuid;
  replay_recheck_id uuid;
  replay_outbox_id uuid;
  replayed boolean;
  replay_next_action text;
BEGIN
  SELECT projection_record.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142';

  SELECT recheck_record.trigger_evidence_acceptance_id
    INTO acceptance_id
    FROM architecture_core.assessment_recheck_request AS recheck_record
   WHERE recheck_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND recheck_record.data_management_assessment_projection_id = projection_id
     AND recheck_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111169';

  IF projection_id IS NULL OR acceptance_id IS NULL THEN
    RAISE EXCEPTION 'reassessment replay fixture is unavailable';
  END IF;

  SELECT
      result.assessment_recheck_request_id,
      result.outbox_event_id,
      result.replayed,
      result.next_action
    INTO replay_recheck_id, replay_outbox_id, replayed, replay_next_action
    FROM architecture_core.request_data_management_assessment_recheck_for_tenant(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      projection_id,
      acceptance_id,
      '0196f300-1111-7111-8111-111111111169',
      '2026-08-19T00:30:00Z'
    ) AS result;

  IF replay_recheck_id IS NULL
     OR replay_outbox_id IS NULL
     OR replayed IS DISTINCT FROM true
     OR replay_next_action IS DISTINCT FROM 'await_assessment_recheck' THEN
    RAISE EXCEPTION
      'exact reassessment retry lacks replay evidence: %, %, %, %',
      replay_recheck_id,
      replay_outbox_id,
      replayed,
      replay_next_action;
  END IF;
END;
$$;
