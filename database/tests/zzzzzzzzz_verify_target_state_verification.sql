\set ON_ERROR_STOP on

-- Buyer acceptance for evidence-backed target-state verification after execution.
-- Completion is not verification: a human-authorized decision must explicitly
-- record whether the target state was verified or a gap was found, with immutable
-- evidence and an atomic privacy-minimized outbox event.

DO $$
BEGIN
  IF to_regclass(
      'architecture_core.transformation_verification_record'
     ) IS NULL THEN
    RAISE EXCEPTION 'target-state verification evidence table is missing';
  END IF;
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
-- rejected command must not leave partial verification/outbox evidence.
DO $$
DECLARE
  verification_count integer;
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

  SELECT count(*) INTO verification_count
    FROM architecture_core.transformation_verification_record
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  IF verification_count <> 0 OR event_count <> 0 THEN
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
  verification_count integer;
  event_count integer;
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

  SELECT count(*) INTO verification_count
    FROM architecture_core.transformation_verification_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND verification_outcome_code = 'verified'
     AND effective_at = '2027-02-02T00:00:00Z'::timestamptz
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
     AND decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  IF verification_count <> 1 THEN
    RAISE EXCEPTION 'verified target-state evidence was not recorded exactly once';
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

-- Exact replay is idempotent and returns the original immutable receipt.
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
  verification_count integer;
  event_count integer;
BEGIN
  SELECT verification_replayed INTO replayed_flag FROM verification_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact target-state verification replay was not idempotent';
  END IF;
  SELECT count(*) INTO verification_count
    FROM architecture_core.transformation_verification_record
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
  IF verification_count <> 1 OR event_count <> 1 THEN
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

-- Verification evidence is append-only and one terminal verification decision
-- owns the completed transformation. Replanning creates a new governed scenario
-- and transformation rather than rewriting the prior decision.
DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.transformation_verification_record
       SET decision_reason_text = 'Mutation must be rejected.'
     WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
    RAISE EXCEPTION 'target-state verification evidence was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    DELETE FROM architecture_core.transformation_verification_record
     WHERE decision_request_id = '0196e0a0-1111-7111-8111-111111111193';
    RAISE EXCEPTION 'target-state verification evidence was deletable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
