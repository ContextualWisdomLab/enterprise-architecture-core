\set ON_ERROR_STOP on

-- Buyer acceptance for the first execution transition after an approved target
-- state has been bound to an authoritative remediation milestone. Starting work
-- appends authoritative transformation history and an outbox event; it does not
-- create project/task execution state.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.start_scheduled_transformation(uuid,uuid,uuid,timestamptz,text,text,uuid)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state start command is missing';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- Work cannot begin before the governed schedule becomes effective. A rejected
-- attempt must leave both history and outbox state unchanged.
DO $$
DECLARE
  history_count integer;
  event_count integer;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.start_scheduled_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e090-1111-7111-8111-111111111190',
          '2027-01-15T23:59:59Z',
          'keyverse:https://id.example/realms/cwl#transformation-operator-123',
          'Do not start before the reviewed schedule is effective.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'backdated transformation start was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111190';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111190';
  IF history_count <> 0 OR event_count <> 0 THEN
    RAISE EXCEPTION 'rejected start partially committed history or outbox state';
  END IF;
END;
$$;

CREATE TEMP TABLE start_receipt AS
SELECT *
  FROM architecture_core.start_scheduled_transformation(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e090-1111-7111-8111-111111111191',
      '2027-01-17T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#transformation-operator-123',
      'Begin the approved target-state execution against the reviewed milestone.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  replayed_flag boolean;
  state_code text;
  action_code text;
  history_count integer;
  event_count integer;
  schedule_count integer;
  leaked_private_context boolean;
BEGIN
  SELECT transformation_state_code, start_replayed, next_action
    INTO state_code, replayed_flag, action_code
    FROM start_receipt;
  IF state_code <> 'started'
     OR replayed_flag
     OR action_code <> 'monitor_transformation' THEN
    RAISE EXCEPTION 'fresh start receipt is not actionable';
  END IF;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND sequence_number = 3
     AND transformation_state_code = 'started'
     AND effective_at = '2027-01-17T00:00:00Z'::timestamptz
     AND truth_status_code = 'authoritative'
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
     AND decision_request_id = '0196e090-1111-7111-8111-111111111191';
  IF history_count <> 1 THEN
    RAISE EXCEPTION 'authoritative started history was not appended exactly once';
  END IF;

  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e090-1111-7111-8111-111111111191'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.started.v1'
     AND aggregate_object_id IS NULL
     AND publish_status_code = 'pending';
  IF event_count <> 1 THEN
    RAISE EXCEPTION 'start outbox event is not exactly-once pending evidence';
  END IF;

  SELECT count(*) INTO schedule_count
    FROM architecture_core.transformation_schedule_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND superseded_at IS NULL;
  IF schedule_count <> 1 THEN
    RAISE EXCEPTION 'starting work mutated or lost the governed schedule binding';
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.outbox_event
       WHERE decision_request_id = '0196e090-1111-7111-8111-111111111191'
         AND (
           event_payload_json ? 'decision_actor_ref'
           OR event_payload_json ? 'decision_reason_text'
         )
  ) INTO leaked_private_context;
  IF leaked_private_context THEN
    RAISE EXCEPTION 'start event leaked private actor/reason context';
  END IF;
END;
$$;

DROP TABLE start_receipt;
CREATE TEMP TABLE start_receipt AS
SELECT *
  FROM architecture_core.start_scheduled_transformation(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e090-1111-7111-8111-111111111191',
      '2027-01-17T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#transformation-operator-123',
      'Begin the approved target-state execution against the reviewed milestone.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  replayed_flag boolean;
  history_count integer;
  event_count integer;
BEGIN
  SELECT start_replayed INTO replayed_flag FROM start_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact transformation start replay was not idempotent';
  END IF;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111191';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111191';
  IF history_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'idempotent start replay duplicated history/event evidence';
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.start_scheduled_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e090-1111-7111-8111-111111111191',
          '2027-01-17T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-operator-123',
          'Conflicting replay must not overwrite the original start meaning.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'conflicting transformation start replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;

-- A second fresh start decision must fail once the authoritative state is
-- already started; execution history cannot fork.
DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.start_scheduled_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e090-1111-7111-8111-111111111192',
          '2027-01-18T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-operator-123',
          'Duplicate start decisions must fail after work has started.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'second transformation start was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
