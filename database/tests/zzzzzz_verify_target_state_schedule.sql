\set ON_ERROR_STOP on

-- Buyer acceptance for the governed step after target-state approval. Scheduling
-- records a durable decision binding to an existing remediation milestone while
-- leaving transformation execution history at `approved` until work really starts.

DO $$
BEGIN
  IF to_regclass('architecture_core.transformation_schedule_record') IS NULL THEN
    RAISE EXCEPTION 'transformation schedule record is missing';
  END IF;
  IF to_regprocedure(
      'architecture_core.schedule_transformation(uuid,uuid,uuid,uuid,timestamptz,text,text,uuid)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state schedule command is missing';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.initiative_milestone (
    tenant_record_id,
    initiative_milestone_id,
    remediation_initiative_id,
    milestone_code,
    milestone_title,
    milestone_description,
    sequence_number,
    target_at,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e060-1111-7111-8111-111111111191',
    '0196e001-1111-7111-8111-111111111111',
    'database_cutover',
    'Database cutover',
    'Milestone selected by the architecture board for the approved target state.',
    2,
    '2027-03-31T00:00:00Z',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

-- A milestone from another remediation initiative cannot be substituted merely
-- because its UUID is valid and visible to the tenant.
DO $$
DECLARE
  schedule_count integer;
  event_count integer;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.schedule_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e070-1111-7111-8111-111111111190',
          '0196b004-1111-7111-8111-111111111111',
          '2027-01-16T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-planner-123',
          'A foreign initiative milestone must not be schedulable.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'cross-initiative milestone was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*) INTO schedule_count
    FROM architecture_core.transformation_schedule_record
   WHERE decision_request_id = '0196e070-1111-7111-8111-111111111190';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e070-1111-7111-8111-111111111190';
  IF schedule_count <> 0 OR event_count <> 0 THEN
    RAISE EXCEPTION 'rejected cross-initiative schedule partially committed';
  END IF;
END;
$$;

-- Scheduling cannot be effective before the approval that grants scheduling
-- authority, even if the selected milestone itself is valid.
DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.schedule_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e070-1111-7111-8111-111111111192',
          '0196e060-1111-7111-8111-111111111191',
          '2027-01-14T23:59:59Z',
          'keyverse:https://id.example/realms/cwl#transformation-planner-123',
          'A schedule cannot precede its approval.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'backdated schedule was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

CREATE TEMP TABLE schedule_receipt AS
SELECT *
  FROM architecture_core.schedule_transformation(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e070-1111-7111-8111-111111111191',
      '0196e060-1111-7111-8111-111111111191',
      '2027-01-16T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#transformation-planner-123',
      'Bind the approved target state to the reviewed database cutover milestone.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  binding_count integer;
  event_count integer;
  approved_state_count integer;
  leaked_private_context boolean;
  replayed_flag boolean;
  target_time timestamptz;
  action_code text;
BEGIN
  SELECT schedule_replayed, milestone_target_at, next_action
    INTO replayed_flag, target_time, action_code
    FROM schedule_receipt;
  IF replayed_flag
     OR target_time <> '2027-03-31T00:00:00Z'::timestamptz
     OR action_code <> 'start_transformation' THEN
    RAISE EXCEPTION 'fresh schedule receipt is not actionable';
  END IF;

  SELECT count(*) INTO binding_count
    FROM architecture_core.transformation_schedule_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND initiative_milestone_id = '0196e060-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e070-1111-7111-8111-111111111191'
     AND effective_at = '2027-01-16T00:00:00Z'::timestamptz
     AND truth_status_code = 'authoritative'
     AND superseded_at IS NULL
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf10';
  IF binding_count <> 1 THEN
    RAISE EXCEPTION 'authoritative schedule binding was not recorded exactly once';
  END IF;

  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e070-1111-7111-8111-111111111191'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.scheduled.v1'
     AND aggregate_object_id IS NULL
     AND publish_status_code = 'pending';
  IF event_count <> 1 THEN
    RAISE EXCEPTION 'schedule outbox event is not exactly-once pending evidence';
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.outbox_event
       WHERE decision_request_id = '0196e070-1111-7111-8111-111111111191'
         AND (
           event_payload_json ? 'decision_actor_ref'
           OR event_payload_json ? 'decision_reason_text'
         )
  ) INTO leaked_private_context;
  IF leaked_private_context THEN
    RAISE EXCEPTION 'schedule event leaked private actor/reason context';
  END IF;

  SELECT count(*) INTO approved_state_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND sequence_number = 2
     AND transformation_state_code = 'approved';
  IF approved_state_count <> 1 THEN
    RAISE EXCEPTION 'scheduling invented an execution state instead of preserving approval';
  END IF;
END;
$$;

DROP TABLE schedule_receipt;
CREATE TEMP TABLE schedule_receipt AS
SELECT *
  FROM architecture_core.schedule_transformation(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e070-1111-7111-8111-111111111191',
      '0196e060-1111-7111-8111-111111111191',
      '2027-01-16T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#transformation-planner-123',
      'Bind the approved target state to the reviewed database cutover milestone.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  replayed_flag boolean;
  schedule_count integer;
  event_count integer;
BEGIN
  SELECT schedule_replayed INTO replayed_flag FROM schedule_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact schedule replay was not identified as idempotent';
  END IF;

  SELECT count(*) INTO schedule_count
    FROM architecture_core.transformation_schedule_record
   WHERE decision_request_id = '0196e070-1111-7111-8111-111111111191';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e070-1111-7111-8111-111111111191';
  IF schedule_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'idempotent schedule replay duplicated binding/event';
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.schedule_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e070-1111-7111-8111-111111111191',
          '0196e060-1111-7111-8111-111111111191',
          '2027-01-16T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-planner-123',
          'Conflicting replay must not overwrite the original schedule meaning.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'conflicting schedule replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;
