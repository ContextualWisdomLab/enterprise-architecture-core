\set ON_ERROR_STOP on

-- Buyer acceptance for closing an already-started target-state transformation.
-- Completion is an EA execution-state decision: it appends authoritative history
-- and an atomic privacy-minimized outbox event without mutating foreign systems,
-- the governed schedule, or project/task execution state.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.complete_started_transformation(uuid,uuid,uuid,timestamptz,text,text,uuid)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state completion command is missing';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- Completion cannot move backward before the recorded start and a rejected
-- attempt must leave both append-only history and outbox evidence untouched.
DO $$
DECLARE
  history_count integer;
  event_count integer;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.complete_started_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e090-1111-7111-8111-111111111193',
          '2027-01-16T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-verifier-123',
          'Completion cannot predate the authoritative start decision.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'backdated transformation completion was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111193';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111193';
  IF history_count <> 0 OR event_count <> 0 THEN
    RAISE EXCEPTION 'rejected completion partially committed history or outbox state';
  END IF;
END;
$$;

CREATE TEMP TABLE completion_receipt AS
SELECT *
  FROM architecture_core.complete_started_transformation(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e090-1111-7111-8111-111111111193',
      '2027-02-01T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#transformation-verifier-123',
      'Confirm the governed target-state execution is complete.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  receipt_state text;
  receipt_next_action text;
  replayed_flag boolean;
  history_count integer;
  event_count integer;
  schedule_count integer;
  leaked_private_context boolean;
BEGIN
  SELECT transformation_state_code, next_action, completion_replayed
    INTO receipt_state, receipt_next_action, replayed_flag
    FROM completion_receipt;
  IF receipt_state <> 'completed'
     OR receipt_next_action <> 'verify_target_state'
     OR replayed_flag THEN
    RAISE EXCEPTION 'fresh completion receipt is not actionable completed evidence';
  END IF;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND sequence_number = 4
     AND transformation_state_code = 'completed'
     AND effective_at = '2027-02-01T00:00:00Z'::timestamptz
     AND truth_status_code = 'authoritative'
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
     AND decision_request_id = '0196e090-1111-7111-8111-111111111193';
  IF history_count <> 1 THEN
    RAISE EXCEPTION 'authoritative completed history was not appended exactly once';
  END IF;

  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e090-1111-7111-8111-111111111193'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.completed.v1'
     AND aggregate_object_id IS NULL
     AND publish_status_code = 'pending';
  IF event_count <> 1 THEN
    RAISE EXCEPTION 'completion outbox event is not exactly-once pending evidence';
  END IF;

  SELECT count(*) INTO schedule_count
    FROM architecture_core.transformation_schedule_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND superseded_at IS NULL;
  IF schedule_count <> 1 THEN
    RAISE EXCEPTION 'completing work mutated or lost the governed schedule binding';
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.outbox_event
       WHERE decision_request_id = '0196e090-1111-7111-8111-111111111193'
         AND (
           event_payload_json ? 'decision_actor_ref'
           OR event_payload_json ? 'decision_reason_text'
         )
  ) INTO leaked_private_context;
  IF leaked_private_context THEN
    RAISE EXCEPTION 'completion event leaked private actor/reason context';
  END IF;
END;
$$;

DROP TABLE completion_receipt;
CREATE TEMP TABLE completion_receipt AS
SELECT *
  FROM architecture_core.complete_started_transformation(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e090-1111-7111-8111-111111111193',
      '2027-02-01T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#transformation-verifier-123',
      'Confirm the governed target-state execution is complete.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  replayed_flag boolean;
  history_count integer;
  event_count integer;
BEGIN
  SELECT completion_replayed INTO replayed_flag FROM completion_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact transformation completion replay was not idempotent';
  END IF;
  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111193';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e090-1111-7111-8111-111111111193';
  IF history_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'idempotent completion replay duplicated immutable evidence';
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.complete_started_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e090-1111-7111-8111-111111111193',
          '2027-02-01T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-verifier-123',
          'Conflicting replay must not overwrite the original completion meaning.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'conflicting transformation completion replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;

-- A terminal completed state cannot accept a second fresh completion decision.
DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.complete_started_transformation(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e090-1111-7111-8111-111111111194',
          '2027-02-02T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#transformation-verifier-123',
          'Duplicate completion decisions must fail after work is completed.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'second transformation completion was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
