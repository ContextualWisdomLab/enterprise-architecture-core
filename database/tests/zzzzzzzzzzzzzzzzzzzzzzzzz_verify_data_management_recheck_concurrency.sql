\set ON_ERROR_STOP on

-- Concurrent exact decision replays must converge on one immutable request and
-- one transactional outbox event. This uses dblink only as an acceptance-test
-- harness so two independent PostgreSQL sessions can race the authoritative
-- command boundary; production code has no dblink dependency.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- Close the second gap on the intentionally partial fixture created by the
-- earlier reassessment acceptance test. That fixture has no recheck request,
-- making it a clean concurrency target.
DO $$
DECLARE
  projection_id uuid;
  plan_id uuid;
  acceptance_id uuid;
  closure_next_action text;
BEGIN
  SELECT projection_record.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f300-1111-7111-8111-111111111162'
     AND projection_record.superseded_at IS NULL;

  IF projection_id IS NULL THEN
    RAISE EXCEPTION 'concurrency reassessment fixture projection is unavailable';
  END IF;

  SELECT result.assessment_improvement_plan_id
    INTO plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'stewardship_evidence',
      '0196f300-1111-7111-8111-111111111171',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_stewardship_evidence_gap_concurrency',
      'Close final gap before concurrent reassessment',
      'stewardship_evidence_accepted_concurrency',
      'Final gap evidence accepted before concurrent reassessment',
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
      '0196f300-1111-7111-8111-111111111172',
      'urn:cwl:tenant_001:semantic_data_portal',
      '0196f300-1111-7111-8111-111111111174',
      repeat('a', 64),
      '1.0.0',
      '2026-08-19T00:35:00Z',
      '2026-08-19T00:35:01Z',
      'processed'
  );

  SELECT
      result.assessment_evidence_acceptance_id,
      result.next_action
    INTO acceptance_id, closure_next_action
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f300-1111-7111-8111-111111111172',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f300-1111-7111-8111-111111111174',
      'observed',
      repeat('a', 64),
      '0196f300-1111-7111-8111-111111111175',
      '2026-08-19T00:35:02Z'
    ) AS result;

  IF acceptance_id IS NULL
     OR closure_next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION
      'concurrency fixture did not close its final gap: %, %',
      acceptance_id,
      closure_next_action;
  END IF;
END;
$$;

CREATE EXTENSION IF NOT EXISTS dblink;

SELECT dblink_connect(
    'recheck_a',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);
SELECT dblink_connect(
    'recheck_b',
    pg_catalog.format('dbname=%s user=%s', current_database(), current_user)
);
SELECT dblink_exec(
    'recheck_a',
    'SET app.tenant_record_id = ''0195d145-64e8-7f4f-8a23-a0cc784cb711'''
);
SELECT dblink_exec(
    'recheck_b',
    'SET app.tenant_record_id = ''0195d145-64e8-7f4f-8a23-a0cc784cb711'''
);

SELECT dblink_send_query(
    'recheck_a',
    $query$
      WITH first_recheck AS MATERIALIZED (
        SELECT
          result.assessment_recheck_request_id::text AS recheck_id,
          result.outbox_event_id::text AS outbox_id,
          result.next_action
        FROM architecture_core.request_data_management_assessment_recheck(
          (
            SELECT projection_record.data_management_assessment_projection_id
              FROM architecture_core.data_management_assessment_projection AS projection_record
             WHERE projection_record.tenant_record_id =
                   '0195d145-64e8-7f4f-8a23-a0cc784cb711'
               AND projection_record.assessment_result_uri =
                   'urn:cwl:tenant_001:data_context:data_management_assessment:0196f300-1111-7111-8111-111111111162'
          ),
          (
            SELECT acceptance_record.assessment_evidence_acceptance_id
              FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
              JOIN architecture_core.assessment_improvement_plan AS plan_record
                ON plan_record.tenant_record_id = acceptance_record.tenant_record_id
               AND plan_record.assessment_improvement_plan_id =
                   acceptance_record.assessment_improvement_plan_id
             WHERE acceptance_record.tenant_record_id =
                   '0195d145-64e8-7f4f-8a23-a0cc784cb711'
               AND plan_record.data_management_assessment_projection_id = (
                 SELECT projection_record.data_management_assessment_projection_id
                   FROM architecture_core.data_management_assessment_projection AS projection_record
                  WHERE projection_record.tenant_record_id =
                        '0195d145-64e8-7f4f-8a23-a0cc784cb711'
                    AND projection_record.assessment_result_uri =
                        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f300-1111-7111-8111-111111111162'
               )
             ORDER BY acceptance_record.accepted_at DESC,
                      acceptance_record.assessment_evidence_acceptance_id DESC
             LIMIT 1
          ),
          '0196f300-1111-7111-8111-111111111176',
          '2026-08-19T00:40:00Z'
        ) AS result
      )
      SELECT
        first_recheck.recheck_id,
        first_recheck.outbox_id,
        first_recheck.next_action,
        pg_sleep(2)::text AS hold_open
      FROM first_recheck;
    $query$
);

-- Let session A enter the command and hold the projection row lock before the
-- second exact replay starts. Session B must wait, then observe A's committed
-- request and return the identical receipt rather than raising unique_violation.
SELECT pg_sleep(0.5);

SELECT dblink_send_query(
    'recheck_b',
    $query$
      SELECT
        result.assessment_recheck_request_id::text AS recheck_id,
        result.outbox_event_id::text AS outbox_id,
        result.next_action
      FROM architecture_core.request_data_management_assessment_recheck(
        (
          SELECT projection_record.data_management_assessment_projection_id
            FROM architecture_core.data_management_assessment_projection AS projection_record
           WHERE projection_record.tenant_record_id =
                 '0195d145-64e8-7f4f-8a23-a0cc784cb711'
             AND projection_record.assessment_result_uri =
                 'urn:cwl:tenant_001:data_context:data_management_assessment:0196f300-1111-7111-8111-111111111162'
        ),
        (
          SELECT acceptance_record.assessment_evidence_acceptance_id
            FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
            JOIN architecture_core.assessment_improvement_plan AS plan_record
              ON plan_record.tenant_record_id = acceptance_record.tenant_record_id
             AND plan_record.assessment_improvement_plan_id =
                 acceptance_record.assessment_improvement_plan_id
           WHERE acceptance_record.tenant_record_id =
                 '0195d145-64e8-7f4f-8a23-a0cc784cb711'
             AND plan_record.data_management_assessment_projection_id = (
               SELECT projection_record.data_management_assessment_projection_id
                 FROM architecture_core.data_management_assessment_projection AS projection_record
                WHERE projection_record.tenant_record_id =
                      '0195d145-64e8-7f4f-8a23-a0cc784cb711'
                  AND projection_record.assessment_result_uri =
                      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f300-1111-7111-8111-111111111162'
             )
           ORDER BY acceptance_record.accepted_at DESC,
                    acceptance_record.assessment_evidence_acceptance_id DESC
           LIMIT 1
        ),
        '0196f300-1111-7111-8111-111111111176',
        '2026-08-19T00:40:00Z'
      ) AS result;
    $query$
);

CREATE TEMP TABLE concurrent_recheck_receipt (
    source_code text NOT NULL,
    assessment_recheck_request_id uuid NOT NULL,
    outbox_event_id uuid NOT NULL,
    next_action text NOT NULL
);

INSERT INTO concurrent_recheck_receipt
SELECT
    'session_a',
    result.recheck_id::uuid,
    result.outbox_id::uuid,
    result.next_action
FROM dblink_get_result('recheck_a') AS result(
    recheck_id text,
    outbox_id text,
    next_action text,
    hold_open text
);

INSERT INTO concurrent_recheck_receipt
SELECT
    'session_b',
    result.recheck_id::uuid,
    result.outbox_id::uuid,
    result.next_action
FROM dblink_get_result('recheck_b') AS result(
    recheck_id text,
    outbox_id text,
    next_action text
);

DO $$
DECLARE
  receipt_count integer;
  recheck_identity_count integer;
  outbox_identity_count integer;
  request_count integer;
  event_count integer;
BEGIN
  SELECT
      count(*),
      count(DISTINCT assessment_recheck_request_id),
      count(DISTINCT outbox_event_id)
    INTO receipt_count, recheck_identity_count, outbox_identity_count
    FROM concurrent_recheck_receipt
   WHERE next_action = 'await_assessment_recheck';

  IF receipt_count <> 2
     OR recheck_identity_count <> 1
     OR outbox_identity_count <> 1 THEN
    RAISE EXCEPTION
      'concurrent exact reassessment replay diverged: %, %, %',
      receipt_count,
      recheck_identity_count,
      outbox_identity_count;
  END IF;

  SELECT count(*)
    INTO request_count
    FROM architecture_core.assessment_recheck_request AS recheck_record
   WHERE recheck_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND recheck_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111176';

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.decision_request_id =
         '0196f300-1111-7111-8111-111111111176'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.assessment_recheck_requested.v1';

  IF request_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION
      'concurrent exact reassessment replay duplicated durable evidence: %, %',
      request_count,
      event_count;
  END IF;
END;
$$;

SELECT dblink_disconnect('recheck_a');
SELECT dblink_disconnect('recheck_b');
DROP EXTENSION dblink;
