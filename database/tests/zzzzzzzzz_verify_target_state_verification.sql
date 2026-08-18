\set ON_ERROR_STOP on

-- Buyer acceptance for evidence-backed target-state verification after execution.
-- Completion is not verification: a human-authorized decision appends a distinct
-- immutable verification state to transformation history and emits atomic,
-- privacy-minimized outbox evidence.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.record_target_state_verification(uuid,uuid,uuid,timestamptz,text,text,uuid,text)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state verification command is missing';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- Verification cannot be backdated before the authoritative completion and a
-- rejected command must leave both append-only history and outbox unchanged.
DO $$
DECLARE
  history_count integer;
  event_count integer;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_verification(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e0a0-1111-7111-8111-111111111193',
          '2027-01-31T23:59:59Z',
          'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
          'Verification cannot predate completed execution evidence.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10',
          'verified'
      );
    RAISE EXCEPTION 'backdated target-state verification was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  IF history_count <> 0 OR event_count <> 0 THEN
    RAISE EXCEPTION 'rejected verification partially committed evidence';
  END IF;
END;
$$;

CREATE TEMP TABLE verification_receipt AS
SELECT *
  FROM architecture_core.record_target_state_verification(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e0a0-1111-7111-8111-111111111193',
      '2027-02-02T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
      'Evidence confirms the approved target state is now in effect.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10',
      'verified'
  );

DO $$
DECLARE
  receipt_outcome text;
  receipt_next_action text;
  replayed_flag boolean;
  history_count integer;
  event_count integer;
  projected_state text;
  leaked_private_context boolean;
BEGIN
  SELECT verification_outcome_code, next_action, verification_replayed
    INTO receipt_outcome, receipt_next_action, replayed_flag
    FROM verification_receipt;
  IF receipt_outcome <> 'verified'
     OR receipt_next_action <> 'monitor_target_state'
     OR replayed_flag THEN
    RAISE EXCEPTION 'fresh target-state verification is not actionable evidence';
  END IF;

  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND sequence_number = 5
     AND transformation_state_code = 'verified'
     AND effective_at = '2027-02-02T00:00:00Z'::timestamptz
     AND truth_status_code = 'authoritative'
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
     AND decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  IF history_count <> 1 THEN
    RAISE EXCEPTION 'verified target-state history was not appended exactly once';
  END IF;

  SELECT transformation_state_code
    INTO projected_state
    FROM architecture_core.project_transformation_state(
        '0196e010-1111-7111-8111-111111111191',
        '2027-02-02T00:00:00Z',
        clock_timestamp()
    );
  IF projected_state <> 'verified' THEN
    RAISE EXCEPTION 'verification state is not visible through bitemporal projection';
  END IF;

  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e0a0-1111-7111-8111-111111111193'
     AND event_type_code =
         'org.contextualwisdomlab.ea.transformation.verification_recorded.v1'
     AND aggregate_object_id IS NULL
     AND publish_status_code = 'pending';
  IF event_count <> 1 THEN
    RAISE EXCEPTION 'verification outbox event is not exactly-once pending evidence';
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.outbox_event
       WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193'
         AND (
           event_payload_json ? 'decision_actor_ref'
           OR event_payload_json ? 'decision_reason_text'
         )
  ) INTO leaked_private_context;
  IF leaked_private_context THEN
    RAISE EXCEPTION 'verification event leaked private actor/reason context';
  END IF;
END;
$$;

-- Exact replay is idempotent and returns the original immutable history/outbox
-- receipt instead of appending another verification state.
DROP TABLE verification_receipt;
CREATE TEMP TABLE verification_receipt AS
SELECT *
  FROM architecture_core.record_target_state_verification(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e0a0-1111-7111-8111-111111111193',
      '2027-02-02T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
      'Evidence confirms the approved target state is now in effect.',
      '0195d145-64e8-7f4f-8a23-a0cc784cbf10',
      'verified'
  );

DO $$
DECLARE
  replayed_flag boolean;
  history_count integer;
  event_count integer;
BEGIN
  SELECT verification_replayed INTO replayed_flag FROM verification_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact target-state verification replay was not idempotent';
  END IF;
  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  IF history_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'verification replay duplicated immutable evidence';
  END IF;
END;
$$;

-- Reusing the decision id with different meaning must fail closed.
DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_verification(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e0a0-1111-7111-8111-111111111193',
          '2027-02-02T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
          'Conflicting replay must not replace the original decision.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10',
          'gap_detected'
      );
    RAISE EXCEPTION 'conflicting target-state verification replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END;
$$;

-- Verification is terminal for this completed transformation. A detected gap
-- or later change is handled by a new governed scenario/transformation rather
-- than rewriting or adding another verification outcome to the old decision.
DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_verification(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e0a0-1111-7111-8111-111111111194',
          '2027-02-03T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
          'A second terminal verification must not rewrite the old decision.',
          '0195d145-64e8-7f4f-8a23-a0cc784cbf10',
          'gap_detected'
      );
    RAISE EXCEPTION 'second terminal target-state verification was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
