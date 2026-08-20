\set ON_ERROR_STOP on

-- Exact concurrent schedule delivery must converge on one schedule/outbox pair.
-- dblink is only a two-session acceptance harness; production has no dependency.

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
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e010-1111-7111-8111-111111111194',
    '0196e002-1111-7111-8111-111111111111',
    '0196e001-1111-7111-8111-111111111111',
    'concurrent_target_schedule',
    'Concurrent target schedule',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
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
    decision_actor_ref,
    decision_reason_text,
    truth_status_code,
    evidence_record_id
) VALUES
(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e020-1111-7111-8111-111111111194',
    '0196e010-1111-7111-8111-111111111194',
    1,
    'proposed',
    '2026-10-01T00:00:00Z',
    'urn:cwl:actor:architecture-board',
    'Concurrent schedule fixture proposal.',
    'proposed',
    NULL
),
(
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e020-1111-7111-8111-111111111195',
    '0196e010-1111-7111-8111-111111111194',
    2,
    'approved',
    '2027-01-15T00:00:00Z',
    'keyverse:https://id.example/realms/cwl#architecture-board-user-789',
    'Approve the fixture before concurrent scheduling.',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

SELECT CASE WHEN EXISTS (
    SELECT 1 FROM pg_catalog.pg_extension WHERE extname = 'dblink'
) THEN 1 ELSE 0 END AS dblink_preexisted
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
SELECT 'session_a', backend_pid
FROM dblink('schedule_a', 'SELECT pg_backend_pid()') AS result(backend_pid integer);
INSERT INTO schedule_backend_session
SELECT 'session_b', backend_pid
FROM dblink('schedule_b', 'SELECT pg_backend_pid()') AS result(backend_pid integer);

CREATE TEMP TABLE concurrent_schedule_receipt (
    source_code text NOT NULL,
    transformation_schedule_record_id uuid NOT NULL,
    outbox_event_id uuid NOT NULL,
    schedule_replayed boolean NOT NULL,
    next_action text NOT NULL
);

SELECT dblink_exec('schedule_a', 'BEGIN');
SELECT dblink_send_query(
    'schedule_a',
    $query$
      SELECT
        transformation_schedule_record_id::text,
        outbox_event_id::text,
        schedule_replayed,
        next_action
      FROM architecture_core.schedule_transformation(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111194',
        '0196e070-1111-7111-8111-111111111194',
        '0196e060-1111-7111-8111-111111111191',
        '2027-01-16T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#transformation-planner-456',
        'Schedule the exact target state once despite concurrent delivery.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      )
    $query$
);
INSERT INTO concurrent_schedule_receipt
SELECT 'session_a', schedule_id::uuid, outbox_id::uuid, replayed, action_code
FROM dblink_get_result('schedule_a') AS result(
    schedule_id text,
    outbox_id text,
    replayed boolean,
    action_code text
);
-- Asynchronous dblink requires one additional empty result read before reuse.
SELECT *
FROM dblink_get_result('schedule_a') AS result(
    schedule_id text,
    outbox_id text,
    replayed boolean,
    action_code text
);

SELECT dblink_send_query(
    'schedule_b',
    $query$
      SELECT
        transformation_schedule_record_id::text,
        outbox_event_id::text,
        schedule_replayed,
        next_action
      FROM architecture_core.schedule_transformation(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111194',
        '0196e070-1111-7111-8111-111111111194',
        '0196e060-1111-7111-8111-111111111191',
        '2027-01-16T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#transformation-planner-456',
        'Schedule the exact target state once despite concurrent delivery.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      )
    $query$
);

DO $$
DECLARE
  a_pid integer;
  b_pid integer;
  blocked boolean := false;
BEGIN
  SELECT backend_pid INTO a_pid
    FROM schedule_backend_session WHERE source_code = 'session_a';
  SELECT backend_pid INTO b_pid
    FROM schedule_backend_session WHERE source_code = 'session_b';
  FOR attempt_number IN 1..100 LOOP
    SELECT EXISTS (
      SELECT 1
      FROM pg_catalog.pg_stat_activity
      WHERE pid = b_pid
        AND wait_event_type = 'Lock'
        AND a_pid = ANY(pg_catalog.pg_blocking_pids(b_pid))
    ) INTO blocked;
    EXIT WHEN blocked;
    PERFORM pg_catalog.pg_sleep(0.05);
  END LOOP;
  IF NOT blocked THEN
    RAISE EXCEPTION 'concurrent schedule replay did not block on session A';
  END IF;
END;
$$;

SELECT dblink_exec('schedule_a', 'COMMIT');
INSERT INTO concurrent_schedule_receipt
SELECT 'session_b', schedule_id::uuid, outbox_id::uuid, replayed, action_code
FROM dblink_get_result('schedule_b') AS result(
    schedule_id text,
    outbox_id text,
    replayed boolean,
    action_code text
);
SELECT *
FROM dblink_get_result('schedule_b') AS result(
    schedule_id text,
    outbox_id text,
    replayed boolean,
    action_code text
);

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
      'concurrent schedule duplicated durable evidence: %, %',
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
