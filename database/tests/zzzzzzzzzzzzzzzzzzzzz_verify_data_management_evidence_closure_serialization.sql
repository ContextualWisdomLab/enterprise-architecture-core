\set ON_ERROR_STOP on

-- Two evidence-closure commands for different gaps of one assessment must
-- serialize on the shared assessment projection before deciding whether a gap
-- is final. Holding that projection row in another session must therefore make
-- this command hit lock_timeout rather than commit independently.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

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
    '0196f500-1111-7111-8111-111111111200',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f500-1111-7111-8111-111111111201',
    repeat('e', 64),
    '1.0.0',
    '2026-08-19T01:10:00Z',
    '2026-08-19T01:10:01Z',
    'processed'
);

CREATE TEMP TABLE evidence_closure_serialization_fixture (
    assessment_projection_id uuid NOT NULL,
    improvement_plan_id uuid NOT NULL
);

DO $$
DECLARE
  projection_id uuid;
  plan_id uuid;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f500-1111-7111-8111-111111111200',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f500-1111-7111-8111-111111111202',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.0.0',
      '2026-08-19T01:09:58Z',
      '2026-08-19T01:09:59Z',
      7300,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f500-1111-7111-8111-111111111203',
      repeat('f', 64),
      'https://example.com/evidence/evidence-closure-serialization',
      NULL,
      ARRAY['serialization_evidence']::text[]
    ) AS result;

  SELECT result.assessment_improvement_plan_id
    INTO plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      projection_id,
      'serialization_evidence',
      '0196f500-1111-7111-8111-111111111204',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_serialization_evidence_gap',
      'Close evidence gap under projection serialization',
      'serialization_evidence_accepted',
      'Evidence accepted under projection serialization',
      '2026-12-31T00:00:00Z',
      NULL
    ) AS result;

  INSERT INTO evidence_closure_serialization_fixture (
      assessment_projection_id,
      improvement_plan_id
  ) VALUES (projection_id, plan_id);
END;
$$;

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
    '0196f500-1111-7111-8111-111111111205',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f500-1111-7111-8111-111111111206',
    repeat('1', 64),
    '1.0.0',
    '2026-08-19T01:10:02Z',
    '2026-08-19T01:10:03Z',
    'processed'
);

\! rm -f /tmp/ea_core_closure_lock_ready /tmp/ea_core_closure_lock_pid
\! sh -c '(printf "%s\n" "BEGIN;" "SELECT set_config('"'"'app.tenant_record_id'"'"', '"'"'0195d145-64e8-7f4f-8a23-a0cc784cb711'"'"', false);" "SELECT data_management_assessment_projection_id FROM architecture_core.data_management_assessment_projection WHERE tenant_record_id = '"'"'0195d145-64e8-7f4f-8a23-a0cc784cb711'"'"' AND assessment_result_uri = '"'"'urn:cwl:tenant_001:data_context:data_management_assessment:0196f500-1111-7111-8111-111111111202'"'"' FOR UPDATE;" "\\! touch /tmp/ea_core_closure_lock_ready" "SELECT pg_sleep(3);" "COMMIT;" | psql --host 127.0.0.1 --username ea_app --dbname ea_core --set ON_ERROR_STOP=1 >/tmp/ea_core_closure_lock.log 2>&1) & echo $! >/tmp/ea_core_closure_lock_pid'
\! sh -c 'i=0; while [ ! -f /tmp/ea_core_closure_lock_ready ]; do i=$((i+1)); if [ "$i" -gt 100 ]; then cat /tmp/ea_core_closure_lock.log >&2; exit 1; fi; sleep 0.05; done'

DO $$
DECLARE
  plan_id uuid;
  lock_blocked boolean := false;
BEGIN
  SELECT improvement_plan_id
    INTO plan_id
    FROM evidence_closure_serialization_fixture;

  PERFORM set_config('lock_timeout', '200ms', true);
  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f500-1111-7111-8111-111111111205',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f500-1111-7111-8111-111111111206',
        'observed',
        repeat('1', 64),
        '0196f500-1111-7111-8111-111111111207',
        '2026-08-19T01:10:04Z'
      );
  EXCEPTION WHEN lock_not_available THEN
    lock_blocked := true;
  END;

  IF NOT lock_blocked THEN
    RAISE EXCEPTION
      'evidence closure did not serialize on the assessment projection row';
  END IF;
END;
$$;

\! sh -c 'pid="$(cat /tmp/ea_core_closure_lock_pid)"; i=0; while kill -0 "$pid" 2>/dev/null; do i=$((i+1)); if [ "$i" -gt 100 ]; then cat /tmp/ea_core_closure_lock.log >&2; kill "$pid" 2>/dev/null || true; exit 1; fi; sleep 0.05; done; cat /tmp/ea_core_closure_lock.log'
\! rm -f /tmp/ea_core_closure_lock_ready /tmp/ea_core_closure_lock_pid /tmp/ea_core_closure_lock.log

-- Exact retries are an idempotency contract under concurrency as well as after
-- commit. Session A records the acceptance while holding its plan-row lock and
-- leaves the transaction open. Session B starts the exact same decision before
-- A commits. It must wait, then re-read the durable decision and return the
-- same receipt instead of misclassifying the retry as a conflicting decision.
\! rm -f /tmp/ea_core_closure_replay_ready /tmp/ea_core_closure_replay_pid /tmp/ea_core_closure_replay.log
\! sh -c '(printf "%s\n" "BEGIN;" "SELECT set_config('"'"'app.tenant_record_id'"'"', '"'"'0195d145-64e8-7f4f-8a23-a0cc784cb711'"'"', false);" "SELECT * FROM architecture_core.accept_data_management_improvement_evidence((SELECT plan_record.assessment_improvement_plan_id FROM architecture_core.assessment_improvement_plan AS plan_record JOIN architecture_core.data_management_assessment_projection AS projection_record ON projection_record.tenant_record_id = plan_record.tenant_record_id AND projection_record.data_management_assessment_projection_id = plan_record.data_management_assessment_projection_id WHERE plan_record.tenant_record_id = '"'"'0195d145-64e8-7f4f-8a23-a0cc784cb711'"'"' AND projection_record.assessment_result_uri = '"'"'urn:cwl:tenant_001:data_context:data_management_assessment:0196f500-1111-7111-8111-111111111202'"'"' AND plan_record.missing_evidence_code = '"'"'serialization_evidence'"'"'), '"'"'0196f500-1111-7111-8111-111111111205'"'"', '"'"'urn:cwl:tenant_001:data_context:assessment_evidence:0196f500-1111-7111-8111-111111111206'"'"', '"'"'observed'"'"', repeat('"'"'1'"'"', 64), '"'"'0196f500-1111-7111-8111-111111111207'"'"', '"'"'2026-08-19T01:10:04Z'"'"');" "\\! touch /tmp/ea_core_closure_replay_ready" "SELECT pg_sleep(3);" "COMMIT;" | psql --host 127.0.0.1 --username ea_app --dbname ea_core --set ON_ERROR_STOP=1 >/tmp/ea_core_closure_replay.log 2>&1) & echo $! >/tmp/ea_core_closure_replay_pid'
\! sh -c 'i=0; while [ ! -f /tmp/ea_core_closure_replay_ready ]; do i=$((i+1)); if [ "$i" -gt 100 ]; then cat /tmp/ea_core_closure_replay.log >&2; exit 1; fi; sleep 0.05; done'

CREATE TEMP TABLE evidence_closure_exact_replay_receipt AS
SELECT result.*
FROM evidence_closure_serialization_fixture AS fixture
CROSS JOIN LATERAL architecture_core.accept_data_management_improvement_evidence(
    fixture.improvement_plan_id,
    '0196f500-1111-7111-8111-111111111205',
    'urn:cwl:tenant_001:data_context:assessment_evidence:0196f500-1111-7111-8111-111111111206',
    'observed',
    repeat('1', 64),
    '0196f500-1111-7111-8111-111111111207',
    '2026-08-19T01:10:04Z'
) AS result;

\! sh -c 'pid="$(cat /tmp/ea_core_closure_replay_pid)"; i=0; while kill -0 "$pid" 2>/dev/null; do i=$((i+1)); if [ "$i" -gt 100 ]; then cat /tmp/ea_core_closure_replay.log >&2; kill "$pid" 2>/dev/null || true; exit 1; fi; sleep 0.05; done; cat /tmp/ea_core_closure_replay.log'

DO $$
DECLARE
  replay_receipt evidence_closure_exact_replay_receipt%ROWTYPE;
  durable_acceptance_id uuid;
  durable_completion_id uuid;
  durable_evidence_event_id uuid;
  durable_milestone_event_id uuid;
  durable_acceptance_count integer;
  durable_evidence_event_count integer;
BEGIN
  SELECT *
    INTO replay_receipt
    FROM evidence_closure_exact_replay_receipt;

  SELECT count(*)
    INTO durable_acceptance_count
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
   WHERE acceptance_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND acceptance_record.decision_request_id =
         '0196f500-1111-7111-8111-111111111207';

  SELECT acceptance_record.assessment_evidence_acceptance_id
    INTO durable_acceptance_id
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
   WHERE acceptance_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND acceptance_record.decision_request_id =
         '0196f500-1111-7111-8111-111111111207'
   LIMIT 1;

  SELECT completion_record.milestone_completion_record_id
    INTO durable_completion_id
    FROM architecture_core.milestone_completion_record AS completion_record
   WHERE completion_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND completion_record.assessment_evidence_acceptance_id = durable_acceptance_id;

  SELECT count(*)
    INTO durable_evidence_event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.decision_request_id =
         '0196f500-1111-7111-8111-111111111207'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1';

  SELECT event_record.outbox_event_id
    INTO durable_evidence_event_id
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.decision_request_id =
         '0196f500-1111-7111-8111-111111111207'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1'
   LIMIT 1;

  SELECT event_record.outbox_event_id
    INTO durable_milestone_event_id
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.causation_event_id = durable_evidence_event_id
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.milestone_completed.v1';

  IF durable_acceptance_count <> 1
     OR durable_evidence_event_count <> 1
     OR replay_receipt.assessment_evidence_acceptance_id IS DISTINCT FROM
        durable_acceptance_id
     OR replay_receipt.milestone_completion_record_id IS DISTINCT FROM
        durable_completion_id
     OR replay_receipt.evidence_outbox_event_id IS DISTINCT FROM
        durable_evidence_event_id
     OR replay_receipt.milestone_outbox_event_id IS DISTINCT FROM
        durable_milestone_event_id
     OR replay_receipt.next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION
      'concurrent exact evidence replay did not converge on one durable receipt';
  END IF;
END;
$$;

\! rm -f /tmp/ea_core_closure_replay_ready /tmp/ea_core_closure_replay_pid /tmp/ea_core_closure_replay.log
