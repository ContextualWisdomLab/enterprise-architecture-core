\set ON_ERROR_STOP on

-- RED concurrency acceptance for the dependency-aware improvement command.
-- The decision must validate prerequisite liveness after it owns the source
-- assessment serialization point. Otherwise a prerequisite can be superseded
-- while the command waits on that source row and still be recorded as active.

aRESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f120-1111-7111-8111-111111111125',
    'urn:cwl:tenant_001:ea_core:initiative_dependency_evidence:0196f120-1111-7111-8111-111111111125',
    repeat('e', 64),
    'https://example.com/evidence/dependency-race-001'
);

INSERT INTO architecture_core.remediation_initiative (
    tenant_record_id,
    remediation_initiative_id,
    initiative_code,
    initiative_title,
    initiative_description,
    valid_from,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f120-1111-7111-8111-111111111126',
    'dependency_race_prerequisite',
    'Dependency race prerequisite',
    'Dedicated prerequisite used to prove liveness is checked after source serialization.',
    '2026-09-01T00:00:00Z',
    'authoritative',
    '0196f120-1111-7111-8111-111111111125'
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
    'dependency_race_a',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);
SELECT dblink_connect(
    'dependency_race_b',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);

SELECT dblink_exec(
    'dependency_race_a',
    'SET app.tenant_record_id = ''0195d145-64e8-7f4f-8a23-a0cc784cb711'''
);
SELECT dblink_exec(
    'dependency_race_b',
    'SET app.tenant_record_id = ''0195d145-64e8-7f4f-8a23-a0cc784cb711'''
);

CREATE TEMP TABLE dependency_race_backend (
    source_code text PRIMARY KEY,
    backend_pid integer NOT NULL
);
INSERT INTO dependency_race_backend
SELECT 'session_a', result.backend_pid
FROM dblink(
    'dependency_race_a',
    'SELECT pg_backend_pid()'
) AS result(backend_pid integer);
INSERT INTO dependency_race_backend
SELECT 'session_b', result.backend_pid
FROM dblink(
    'dependency_race_b',
    'SELECT pg_backend_pid()'
) AS result(backend_pid integer);

SELECT dblink_exec('dependency_race_a', 'BEGIN');
SELECT dblink_exec(
    'dependency_race_a',
    $lock$
      SELECT 1
        FROM architecture_core.data_management_assessment_projection
       WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
         AND assessment_result_uri =
             'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111'
       FOR UPDATE
    $lock$
);

SELECT dblink_exec(
    'dependency_race_b',
    $remote$
      CREATE FUNCTION pg_temp.try_dependency_after_wait()
      RETURNS text
      LANGUAGE plpgsql
      AS $function$
      BEGIN
        BEGIN
          PERFORM *
            FROM architecture_core.create_data_management_improvement_plan(
              (
                SELECT data_management_assessment_projection_id
                  FROM architecture_core.data_management_assessment_projection
                 WHERE tenant_record_id =
                       '0195d145-64e8-7f4f-8a23-a0cc784cb711'
                   AND assessment_result_uri =
                       'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111'
              ),
              'stewardship_evidence',
              '0196f120-1111-7111-8111-111111111127',
              '0195d145-64e8-7f4f-8a23-a0cc784cb901',
              '0196f100-1111-7111-8111-111111111110',
              'reject_superseded_dependency_race',
              'Reject superseded dependency race',
              'dependency_race_guard',
              'Dependency race guard',
              '2027-03-31T00:00:00Z',
              NULL,
              ARRAY['0196f120-1111-7111-8111-111111111126'::uuid],
              ARRAY['0196f120-1111-7111-8111-111111111125'::uuid]
            );
          RETURN 'accepted';
        EXCEPTION WHEN check_violation THEN
          RETURN 'rejected';
        END;
      END;
      $function$
    $remote$
);

SELECT dblink_send_query(
    'dependency_race_b',
    'SELECT pg_temp.try_dependency_after_wait() AS decision_result'
);

DO $$
DECLARE
  session_a_pid integer;
  session_b_pid integer;
  is_blocked boolean := false;
BEGIN
  SELECT backend_pid INTO session_a_pid
    FROM dependency_race_backend
   WHERE source_code = 'session_a';
  SELECT backend_pid INTO session_b_pid
    FROM dependency_race_backend
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
      'dependency decision did not reach the source-assessment serialization wait';
  END IF;
END;
$$;

SELECT dblink_exec(
    'dependency_race_a',
    $supersede$
      UPDATE architecture_core.remediation_initiative
         SET superseded_at = clock_timestamp()
       WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
         AND remediation_initiative_id =
             '0196f120-1111-7111-8111-111111111126'
    $supersede$
);
SELECT dblink_exec('dependency_race_a', 'COMMIT');

CREATE TEMP TABLE dependency_race_result (
    decision_result text NOT NULL
);
INSERT INTO dependency_race_result
SELECT result.decision_result
FROM dblink_get_result('dependency_race_b') AS result(decision_result text);

DO $$
DECLARE
  observed_result text;
  durable_plan_count integer;
BEGIN
  SELECT decision_result INTO observed_result
    FROM dependency_race_result;

  SELECT count(*) INTO durable_plan_count
    FROM architecture_core.assessment_improvement_plan
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196f120-1111-7111-8111-111111111127';

  IF observed_result IS DISTINCT FROM 'rejected'
     OR durable_plan_count <> 0 THEN
    RAISE EXCEPTION
      'superseded prerequisite race was accepted: result %, durable plans %',
      observed_result,
      durable_plan_count;
  END IF;
END;
$$;

SELECT dblink_disconnect('dependency_race_a');
SELECT dblink_disconnect('dependency_race_b');
\if :dblink_preexisted
\else
DROP EXTENSION dblink;
\endif
