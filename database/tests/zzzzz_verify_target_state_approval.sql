\set ON_ERROR_STOP on

-- RED/GREEN acceptance for the first purpose-bound human approval command.
-- The command must append authoritative transformation history and an outbox
-- event atomically, bind the verified tenant/actor, and replay idempotently.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.approve_target_state(uuid,uuid,uuid,timestamptz,text,text,uuid)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state approval command is missing';
  END IF;
END;
$$;

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
    '0196e010-1111-7111-8111-111111111191',
    '0196e002-1111-7111-8111-111111111111',
    '0196e001-1111-7111-8111-111111111111',
    'database_target_approval_api',
    'Database target approval API',
    'Exercise one purpose-bound human target-state approval command.',
    '2026-08-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    '2026-09-01T00:00:00Z',
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
    '0196e020-1111-7111-8111-111111111191',
    '0196e010-1111-7111-8111-111111111191',
    1,
    'proposed',
    '2026-10-01T00:00:00Z',
    '2026-10-01T01:00:00Z',
    'urn:cwl:actor:architecture-board',
    'Target-state evidence is ready for governed approval.',
    'proposed'
);

CREATE TEMP TABLE approval_receipt AS
SELECT *
  FROM architecture_core.approve_target_state(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e030-1111-7111-8111-111111111191',
      '2027-01-15T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#architecture-board-user-123',
      'Architecture board approved the reviewed target state and remediation evidence.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  approved_count integer;
  emitted_count integer;
  leaked_private_context boolean;
  state_code text;
  replayed_flag boolean;
BEGIN
  SELECT transformation_state_code, replayed
    INTO state_code, replayed_flag
    FROM approval_receipt;
  IF state_code <> 'approved' OR replayed_flag THEN
    RAISE EXCEPTION 'first approval did not produce a fresh approved receipt';
  END IF;

  SELECT count(*)
    INTO approved_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND transformation_state_code = 'approved'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111191'
     AND decision_actor_ref =
         'keyverse:https://id.example/realms/cwl#architecture-board-user-123'
     AND decision_reason_text =
         'Architecture board approved the reviewed target state and remediation evidence.'
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf10';
  IF approved_count <> 1 THEN
    RAISE EXCEPTION 'approval history is not exact/auditable: %', approved_count;
  END IF;

  SELECT count(*)
    INTO emitted_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111191'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.approved.v1'
     AND aggregate_object_id IS NULL
     AND publish_status_code = 'pending';
  IF emitted_count <> 1 THEN
    RAISE EXCEPTION 'approval outbox event is not exactly-once pending evidence: %', emitted_count;
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.outbox_event
       WHERE decision_request_id = '0196e030-1111-7111-8111-111111111191'
         AND (
           event_payload_json ? 'decision_actor_ref'
           OR event_payload_json ? 'decision_reason_text'
         )
  ) INTO leaked_private_context;
  IF leaked_private_context THEN
    RAISE EXCEPTION 'approval event leaked actor/reason context outside the audit record';
  END IF;
END;
$$;

DROP TABLE approval_receipt;
CREATE TEMP TABLE approval_receipt AS
SELECT *
  FROM architecture_core.approve_target_state(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e030-1111-7111-8111-111111111191',
      '2027-01-15T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#architecture-board-user-123',
      'Architecture board approved the reviewed target state and remediation evidence.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
  );

DO $$
DECLARE
  history_count integer;
  event_count integer;
  replayed_flag boolean;
BEGIN
  SELECT replayed INTO replayed_flag FROM approval_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact decision replay was not identified as idempotent';
  END IF;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111191';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111191';
  IF history_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'idempotent replay duplicated history/event: %, %', history_count, event_count;
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.approve_target_state(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e030-1111-7111-8111-111111111191',
          '2027-01-15T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#architecture-board-user-123',
          'Conflicting replay must not overwrite the original approval meaning.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
      );
    RAISE EXCEPTION 'conflicting idempotency replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;

DO $$
DECLARE
  failed_history_count integer;
  failed_event_count integer;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.approve_target_state(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e030-1111-7111-8111-111111111192',
          '2027-01-16T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#architecture-board-user-123',
          'A failed approval must not partially commit history or outbox state.',
          '0196efff-ffff-7fff-8fff-ffffffffffff'
      );
    RAISE EXCEPTION 'approval with missing evidence was accepted';
  EXCEPTION WHEN foreign_key_violation THEN
    NULL;
  END;

  SELECT count(*) INTO failed_history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111192';
  SELECT count(*) INTO failed_event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e030-1111-7111-8111-111111111192';
  IF failed_history_count <> 0 OR failed_event_count <> 0 THEN
    RAISE EXCEPTION 'failed approval partially committed history/event';
  END IF;
END;
$$;
