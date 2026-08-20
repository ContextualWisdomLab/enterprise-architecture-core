\set ON_ERROR_STOP on

-- Exact concurrent schedule delivery must converge on one immutable binding and
-- one transactional outbox event rather than racing the unique constraints.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.architecture_transformation (
    tenant_record_id,
    architecture_transformation_id,
    architecture_scenario_id,
    remediation_initiative_id,
    transformation_code,
    transformation_title,
    transformation_description,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e010-1111-7111-8111-111111111194',
    '0196e002-1111-7111-8111-111111111111',
    '0196e001-1111-7111-8111-111111111111',
    'concurrent_target_schedule',
    'Concurrent target schedule',
    'Exercise exact concurrent schedule delivery against one approved target state.',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    clock_timestamp() - interval '2 seconds',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.transformation_history_record (
    tenant_record_id,
    transformation_history_record_id,
    architecture_transformation_id,
    sequence_number,
    transformation_state_code,
    effective_at,
    recorded_at,
    decision_actor_ref,
    decision_reason_text,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e020-1111-7111-8111-111111111194',
    '0196e010-1111-7111-8111-111111111194',
    1,
    'proposed',
    '2026-10-01T00:00:00Z',
    clock_timestamp() - interval '1 second',
    'urn:cwl:actor:architecture-board',
    'Concurrent schedule acceptance fixture.',
    'proposed'
);

PERFORM *
FROM architecture_core.approve_target_state(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e010-1111-7111-8111-111111111194',
    '0196e030-1111-7111-8111-111111111194',
    '2027-01-15T00:00:00Z',
    'keyverse:https://id.example/realms/cwl#architecture-board-user-789',
    'Approve the fixture before concurrent scheduling.',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

SELECT CASE
         WHEN EXISTS (
           SELECT 1 FROM pg_catalog.pg_extension WHERE extname = 'dblink'
         ) THEN 1 ELSE 0
       END AS dblink_preexisted
\gset
CREATE EXTENSION IF NOT EXISTS dblink;

SELECT dblink_connect(
    'schedule_a',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);
SELECT dblink_connect(
    'schedule_b',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);

CREATE TEMP TABLE schedule_backend_session (
    source_code text PRIMARY KEY,
    backend_pid integer NOT NULL
);
INSERT INTO schedule_backend_session
SELECT 'session_a', result.backend_pid
FROM dblink('schedule_a', 'SELECT pg_backend_pid()') AS result(backend_pid integer);
INSERT INTO schedule_backend_session
SELECT 'session_b', result.backend_pid
FROM dblink('schedule_b', 'SELECT pg_backend_pid()') AS result(backend_pid integer);

SELECT dblink_exec('schedule_a', 'BEGIN');
SELECT dblink_exec(
    'schedule_a',
    $lock$
      SELECT 1
        FROM architecture_core.architecture_transformation
       WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
         AND architecture_transformation_id =
             '0196e010-1111-7111-8111-111111111194'
       FOR UPDATE
    $lock$
);

SELECT dblink_send_query(
    'schedule_a',
    $query$
      SELECT
        result.transformation_schedule_record_id::text AS schedule_id,
        result.outbox_event_id::text AS outbox_id,
        result.schedule_replayed,
        result.next_action
      FROM architecture_core.schedule_transformation(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111194',
        '0196e070-1111-7111-8111-111111111194',
        '0196e060-1111-7111-8111-111111111191',
        '2027-01-16T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#transformation-planner-456',
        'Schedule the exact target state once despite concurrent delivery.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      ) AS result
    $query$
);

CREATE TEMP TABLE concurrent_schedule_receipt (
    source_code text NOT NULL,
    transformation_schedule_record_id uuid NOT NULL,
    outbox_event_id uuid NOT NULL,
    schedule_replayed boolean NOT NULL,
    next_action text NOT NULL
);

INSERT INTO concurrent_schedule_receipt
SELECT
    'session_a',
    result.schedule_id::uuid,
    result.outbox_id::uuid,
    result.schedule_replayed,
    result.next_action
FROM dblink_get_result('schedule_a') AS result(
    schedule_id text,
    outbox_id text,
    schedule_replayed boolean,
    next_action text
);

DO $$
DECLARE
  trailing_result_count integer;
BEGIN
  SELECT count(*) INTO trailing_result_count
    FROM dblink_get_result('schedule_a') AS result(
      schedule_id text,
      outbox_id text,
      schedule_replayed boolean,
      next_action text
    );
  IF trailing_result_count <> 0 THEN
    RAISE EXCEPTION 'session A returned an unexpected trailing schedule result';
  END IF;
END;
$$;

SELECT dblink_send_query(
    'schedule_b',
    $query$
      SELECT
        result.transformation_schedule_record_id::text AS schedule_id,
        result.outbox_event_id::text AS outbox_id,
        result.schedule_replayed,
        result.next_action
      FROM architecture_core.schedule_transformation(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111194',
        '0196e070-1111-7111-8111-111111111194',
        '0196e060-1111-7111-8111-111111111191',
        '2027-01-16T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#transformation-planner-456',
        'Schedule the exact target state once despite concurrent delivery.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      ) AS result
    $query$
);

DO $$
DECLARE
  session_a_pid integer;
  session_b_pid integer;
  is_blocked boolean := false;
BEGIN
  SELECT backend_pid INTO session_a_pid
    FROM schedule_backend_session WHERE source_code = 'session_a';
  SELECT backend_pid INTO session_b_pid
    FROM schedule_backend_session WHERE source_code = 'session_b';

  FOR attempt_number IN 1..100 LOOP
    SELECT EXISTS (
        SELECT 1
          FROM pg_catalog.pg_stat_activity AS activity_record
         WHERE activity_record.pid = session_b_pid
           AND activity_record.wait_event_type = 'Lock'
           AND session_a_pid = ANY(pg_catalog.pg_blocking_pids(session_b_pid))
    ) INTO is_blocked;
    EXIT WHEN is_blocked;
    PERFORM pg_catalog.pg_sleep(0.05);
  END LOOP;

  IF NOT is_blocked THEN
    RAISE EXCEPTION
      'concurrent schedule replay was not blocked by the target aggregate owner';
  END IF;
END;
$$;

SELECT dblink_exec('schedule_a', 'COMMIT');

INSERT INTO concurrent_schedule_receipt
SELECT
    'session_b',
    result.schedule_id::uuid,
    result.outbox_id::uuid,
    result.schedule_replayed,
    result.next_action
FROM dblink_get_result('schedule_b') AS result(
    schedule_id text,
    outbox_id text,
    schedule_replayed boolean,
    next_action text
);

DO $$
DECLARE
  trailing_result_count integer;
BEGIN
  SELECT count(*) INTO trailing_result_count
    FROM dblink_get_result('schedule_b') AS result(
      schedule_id text,
      outbox_id text,
      schedule_replayed boolean,
      next_action text
    );
  IF trailing_result_count <> 0 THEN
    RAISE EXCEPTION 'session B returned an unexpected trailing schedule result';
  END IF;
END;
$$;

DO $$
DECLARE
  receipt_count integer;
  schedule_identity_count integer;
  outbox_identity_count integer;
  replayed_count integer;
  durable_schedule_count integer;
  durable_event_count integer;
BEGIN
  SELECT
      count(*),
      count(DISTINCT transformation_schedule_record_id),
      count(DISTINCT outbox_event_id),
      count(*) FILTER (WHERE schedule_replayed)
    INTO receipt_count, schedule_identity_count, outbox_identity_count, replayed_count
    FROM concurrent_schedule_receipt
   WHERE next_action = 'start_transformation';

  IF receipt_count <> 2
     OR schedule_identity_count <> 1
     OR outbox_identity_count <> 1
     OR replayed_count <> 1 THEN
    RAISE EXCEPTION
      'concurrent exact schedule replay diverged: %, %, %, %',
      receipt_count,
      schedule_identity_count,
      outbox_identity_count,
      replayed_count;
  END IF;

  SELECT count(*) INTO durable_schedule_count
    FROM architecture_core.transformation_schedule_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e070-1111-7111-8111-111111111194';
  SELECT count(*) INTO durable_event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e070-1111-7111-8111-111111111194'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.scheduled.v1';

  IF durable_schedule_count <> 1 OR durable_event_count <> 1 THEN
    RAISE EXCEPTION
      'concurrent exact schedule duplicated durable evidence: %, %',
      durable_schedule_count,
      durable_event_count;
  END IF;
END;
$$;

SELECT dblink_disconnect('schedule_a');
SELECT dblink_disconnect('schedule_b');
\if :dblink_preexisted
\else
DROP EXTENSION dblink;
\endif
