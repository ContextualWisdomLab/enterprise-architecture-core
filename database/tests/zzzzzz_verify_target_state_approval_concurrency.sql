\set ON_ERROR_STOP on

-- Concurrent exact approval decisions must converge on one immutable history
-- record and one transactional outbox event. dblink is used only as a two-session
-- acceptance harness; production approval behavior has no dblink dependency.

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
    '0196e010-1111-7111-8111-111111111192',
    '0196e002-1111-7111-8111-111111111111',
    '0196e001-1111-7111-8111-111111111111',
    'concurrent_target_approval',
    'Concurrent target approval',
    'Prove exact concurrent approval decisions converge on one durable receipt.',
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
    '0196e020-1111-7111-8111-111111111192',
    '0196e010-1111-7111-8111-111111111192',
    1,
    'proposed',
    '2026-10-01T00:00:00Z',
    clock_timestamp() - interval '1 second',
    'urn:cwl:actor:architecture-board',
    'Concurrent approval acceptance fixture.',
    'proposed'
);

SELECT CASE
         WHEN EXISTS (
           SELECT 1
             FROM pg_catalog.pg_extension
            WHERE extname = 'dblink'
         ) THEN 1
         ELSE 0
       END AS dblink_preexisted
\gset
CREATE EXTENSION IF NOT EXISTS dblink;

SELECT dblink_connect(
    'approval_a',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);
SELECT dblink_connect(
    'approval_b',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);

CREATE TEMP TABLE approval_backend_session (
    source_code text PRIMARY KEY,
    backend_pid integer NOT NULL
);
INSERT INTO approval_backend_session
SELECT 'session_a', result.backend_pid
FROM dblink('approval_a', 'SELECT pg_backend_pid()') AS result(backend_pid integer);
INSERT INTO approval_backend_session
SELECT 'session_b', result.backend_pid
FROM dblink('approval_b', 'SELECT pg_backend_pid()') AS result(backend_pid integer);

-- Hold the transformation aggregate in A. The defective implementation checks
-- replay state before this lock, so B can observe no committed decision and then
-- block here. A repaired implementation serializes before replay lookup and sees
-- A's durable receipt after COMMIT. dblink_exec cannot execute a row-returning
-- SELECT, so acquire the same row lock inside a no-result DO command.
SELECT dblink_exec('approval_a', 'BEGIN');
SELECT dblink_exec(
    'approval_a',
    $lock$
      DO $approval_lock$
      BEGIN
        PERFORM 1
          FROM architecture_core.architecture_transformation
         WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
           AND architecture_transformation_id =
               '0196e010-1111-7111-8111-111111111192'
         FOR UPDATE;
      END
      $approval_lock$;
    $lock$
);

SELECT dblink_send_query(
    'approval_a',
    $query$
      SELECT
        result.transformation_history_record_id::text AS history_id,
        result.outbox_event_id::text AS outbox_id,
        result.approval_replayed,
        result.next_action
      FROM architecture_core.approve_target_state(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111192',
        '0196e030-1111-7111-8111-111111111193',
        '2027-01-15T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#architecture-board-user-456',
        'Approve the exact target state once despite concurrent delivery.',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      ) AS result
    $query$
);

CREATE TEMP TABLE concurrent_approval_receipt (
    source_code text NOT NULL,
    transformation_history_record_id uuid NOT NULL,
    outbox_event_id uuid NOT NULL,
    approval_replayed boolean NOT NULL,
    next_action text NOT NULL
);

INSERT INTO concurrent_approval_receipt
SELECT
    'session_a',
    result.history_id::uuid,
    result.outbox_id::uuid,
    result.approval_replayed,
    result.next_action
FROM dblink_get_result('approval_a') AS result(
    history_id text,
    outbox_id text,
    approval_replayed boolean,
    next_action text
);

DO $$
DECLARE
  trailing_result_count integer;
BEGIN
  SELECT count(*)
    INTO trailing_result_count
    FROM dblink_get_result('approval_a') AS result(
      history_id text,
      outbox_id text,
      approval_replayed boolean,
      next_action text
    );
  IF trailing_result_count <> 0 THEN
    RAISE EXCEPTION
      'session A returned an unexpected trailing asynchronous result: %',
      trailing_result_count;
  END IF;
END;
$$;

SELECT dblink_send_query(
    'approval_b',
    $query$
      SELECT
        result.transformation_history_record_id::text AS history_id,
        result.outbox_event_id::text AS outbox_id,
        result.approval_replayed,
        result.next_action
      FROM architecture_core.approve_target_state(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e010-1111-7111-8111-111111111192',
        '0196e030-1111-7111-8111-111111111193',
        '2027-01-15T00:00:00Z',
        'keyverse:https://id.example/realms/cwl#architecture-board-user-456',
        'Approve the exact target state once despite concurrent delivery.',
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
    FROM approval_backend_session
   WHERE source_code = 'session_a';
  SELECT backend_pid INTO session_b_pid
    FROM approval_backend_session
   WHERE source_code = 'session_b';

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
      'concurrent approval replay was not blocked by the target aggregate owner';
  END IF;
END;
$$;

SELECT dblink_exec('approval_a', 'COMMIT');

INSERT INTO concurrent_approval_receipt
SELECT
    'session_b',
    result.history_id::uuid,
    result.outbox_id::uuid,
    result.approval_replayed,
    result.next_action
FROM dblink_get_result('approval_b') AS result(
    history_id text,
    outbox_id text,
    approval_replayed boolean,
    next_action text
);

DO $$
DECLARE
  trailing_result_count integer;
BEGIN
  SELECT count(*)
    INTO trailing_result_count
    FROM dblink_get_result('approval_b') AS result(
      history_id text,
      outbox_id text,
      approval_replayed boolean,
      next_action text
    );
  IF trailing_result_count <> 0 THEN
    RAISE EXCEPTION
      'session B returned an unexpected trailing asynchronous result: %',
      trailing_result_count;
  END IF;
END;
$$;

DO $$
DECLARE
  receipt_count integer;
  history_identity_count integer;
  outbox_identity_count integer;
  replayed_count integer;
  durable_history_count integer;
  durable_event_count integer;
BEGIN
  SELECT
      count(*),
      count(DISTINCT transformation_history_record_id),
      count(DISTINCT outbox_event_id),
      count(*) FILTER (WHERE approval_replayed)
    INTO
      receipt_count,
      history_identity_count,
      outbox_identity_count,
      replayed_count
    FROM concurrent_approval_receipt
   WHERE next_action = 'schedule_transformation';

  IF receipt_count <> 2
     OR history_identity_count <> 1
     OR outbox_identity_count <> 1
     OR replayed_count <> 1 THEN
    RAISE EXCEPTION
      'concurrent exact approval replay diverged: %, %, %, %',
      receipt_count,
      history_identity_count,
      outbox_identity_count,
      replayed_count;
  END IF;

  SELECT count(*) INTO durable_history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111193';
  SELECT count(*) INTO durable_event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111193'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.approved.v1';

  IF durable_history_count <> 1 OR durable_event_count <> 1 THEN
    RAISE EXCEPTION
      'concurrent exact approval duplicated durable evidence: %, %',
      durable_history_count,
      durable_event_count;
  END IF;
END;
$$;

SELECT dblink_disconnect('approval_a');
SELECT dblink_disconnect('approval_b');
\if :dblink_preexisted
\else
DROP EXTENSION dblink;
\endif
