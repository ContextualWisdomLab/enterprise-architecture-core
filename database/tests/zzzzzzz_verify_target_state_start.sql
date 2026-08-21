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

-- Two delivery workers can race the same idempotency key in production. Hold
-- the aggregate row long enough for both independent sessions to reach the
-- serialization boundary, then prove one execution and one exact replay return
-- the same committed receipt instead of turning the loser into a state error.
CREATE EXTENSION IF NOT EXISTS dblink;
SELECT dblink_connect(
    'start_race_one',
    'host=127.0.0.1 port=5432 dbname=ea_core user=ea_app password=ea_test_password application_name=start_race_one'
);
SELECT dblink_connect(
    'start_race_two',
    'host=127.0.0.1 port=5432 dbname=ea_core user=ea_app password=ea_test_password application_name=start_race_two'
);

BEGIN;
SELECT 1
  FROM architecture_core.architecture_transformation
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
 FOR UPDATE;

SELECT dblink_send_query(
    'start_race_one',
    $$SELECT * FROM architecture_core.start_scheduled_transformation(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        '0196e090-1111-7111-8111-111111111191',
        '2027-01-17T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#transformation-operator-123',
        'Begin the approved target-state execution against the reviewed milestone.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    )$$
);
SELECT dblink_send_query(
    'start_race_two',
    $$SELECT * FROM architecture_core.start_scheduled_transformation(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111191',
        '0196e090-1111-7111-8111-111111111191',
        '2027-01-17T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#transformation-operator-123',
        'Begin the approved target-state execution against the reviewed milestone.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    )$$
);

DO $$
DECLARE
  blocked_worker_count integer;
  poll_attempt integer := 0;
BEGIN
  LOOP
    SELECT count(*)
      INTO blocked_worker_count
      FROM pg_catalog.pg_stat_activity
     WHERE application_name IN ('start_race_one', 'start_race_two')
       AND wait_event_type = 'Lock';
    EXIT WHEN blocked_worker_count = 2;
    poll_attempt := poll_attempt + 1;
    IF poll_attempt > 200 THEN
      RAISE EXCEPTION 'concurrent start workers did not reach the aggregate lock';
    END IF;
    PERFORM pg_catalog.pg_sleep(0.01);
  END LOOP;
END;
$$;
COMMIT;

CREATE TEMP TABLE start_receipt (
    transformation_history_record_id uuid,
    architecture_transformation_id uuid,
    transformation_state_code text,
    outbox_event_id uuid,
    decision_request_id uuid,
    start_recorded_at timestamptz,
    start_replayed boolean,
    next_action text
);

INSERT INTO start_receipt
SELECT *
  FROM dblink_get_result('start_race_one') AS race_receipt(
      transformation_history_record_id uuid,
      architecture_transformation_id uuid,
      transformation_state_code text,
      outbox_event_id uuid,
      decision_request_id uuid,
      start_recorded_at timestamptz,
      start_replayed boolean,
      next_action text
  );
INSERT INTO start_receipt
SELECT *
  FROM dblink_get_result('start_race_two') AS race_receipt(
      transformation_history_record_id uuid,
      architecture_transformation_id uuid,
      transformation_state_code text,
      outbox_event_id uuid,
      decision_request_id uuid,
      start_recorded_at timestamptz,
      start_replayed boolean,
      next_action text
  );
SELECT dblink_disconnect('start_race_one');
SELECT dblink_disconnect('start_race_two');
DROP EXTENSION dblink;

DO $$
DECLARE
  receipt_count integer;
  fresh_count integer;
  replay_count integer;
  state_count integer;
  identity_count integer;
  history_count integer;
  event_count integer;
  schedule_count integer;
  leaked_private_context boolean;
BEGIN
  SELECT
      count(*),
      count(*) FILTER (WHERE NOT start_replayed),
      count(*) FILTER (WHERE start_replayed),
      count(*) FILTER (
          WHERE transformation_state_code = 'started'
            AND next_action = 'monitor_transformation'
      ),
      count(DISTINCT (
          transformation_history_record_id,
          outbox_event_id,
          decision_request_id
      ))
    INTO receipt_count, fresh_count, replay_count, state_count, identity_count
    FROM start_receipt;
  IF receipt_count <> 2
     OR fresh_count <> 1
     OR replay_count <> 1
     OR state_count <> 2
     OR identity_count <> 1 THEN
    RAISE EXCEPTION 'concurrent exact start did not converge on one receipt';
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
