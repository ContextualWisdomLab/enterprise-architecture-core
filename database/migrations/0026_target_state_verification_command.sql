BEGIN;

-- Completion means the governed execution finished; it does not prove that the
-- approved target state exists. Extend the append-only transformation history
-- with two explicit terminal verification outcomes rather than adding a second
-- mutable status surface.
ALTER TABLE architecture_core.transformation_history_record
    DROP CONSTRAINT transformation_history_record_state_allowed,
    ADD CONSTRAINT transformation_history_record_state_allowed
        CHECK (
            transformation_state_code IN (
                'proposed',
                'approved',
                'started',
                'completed',
                'verified',
                'gap_detected',
                'cancelled',
                'rejected'
            )
        ),
    DROP CONSTRAINT transformation_history_record_decision_authority,
    ADD CONSTRAINT transformation_history_record_decision_authority
        CHECK (
            transformation_state_code NOT IN (
                'approved',
                'verified',
                'gap_detected',
                'cancelled',
                'rejected'
            )
            OR truth_status_code = 'authoritative'
        );

CREATE OR REPLACE FUNCTION architecture_core.validate_transformation_history_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  transformation_valid_from timestamptz;
  transformation_valid_to timestamptz;
  transformation_superseded_at timestamptz;
  transformation_truth_status_code text;
  previous_sequence_number integer;
  previous_state_code text;
  previous_effective_at timestamptz;
  previous_recorded_at timestamptz;
  transition_allowed boolean := false;
BEGIN
  SELECT
      valid_from,
      valid_to,
      superseded_at,
      truth_status_code
    INTO
      transformation_valid_from,
      transformation_valid_to,
      transformation_superseded_at,
      transformation_truth_status_code
    FROM architecture_core.architecture_transformation
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_transformation_id = NEW.architecture_transformation_id;

  IF transformation_valid_from IS NOT NULL
     AND (
        transformation_superseded_at IS NOT NULL
        OR transformation_truth_status_code IN ('superseded', 'rejected')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'history cannot be appended to an inactive transformation';
  END IF;

  IF NEW.transformation_state_code IN (
        'approved',
        'started',
        'completed',
        'verified',
        'gap_detected',
        'cancelled'
     )
     AND transformation_truth_status_code <> 'authoritative' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'governed execution or verification state requires authoritative transformation';
  END IF;

  IF transformation_valid_from IS NOT NULL
     AND NOT (
        NEW.effective_at
        <@ tstzrange(
            transformation_valid_from,
            transformation_valid_to,
            '[)'
        )
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation state lies outside transformation validity';
  END IF;

  SELECT
      sequence_number,
      transformation_state_code,
      effective_at,
      recorded_at
    INTO
      previous_sequence_number,
      previous_state_code,
      previous_effective_at,
      previous_recorded_at
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_transformation_id = NEW.architecture_transformation_id
   ORDER BY sequence_number DESC
   LIMIT 1;

  IF previous_sequence_number IS NULL THEN
    IF NEW.sequence_number <> 1
       OR NEW.transformation_state_code <> 'proposed' THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'transformation history must begin with proposed sequence 1';
    END IF;
    RETURN NEW;
  END IF;

  IF NEW.sequence_number <> previous_sequence_number + 1 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation history sequence must be contiguous';
  END IF;

  IF NEW.effective_at < previous_effective_at
     OR NEW.recorded_at < previous_recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation history cannot move backward in time';
  END IF;

  transition_allowed := CASE previous_state_code
    WHEN 'proposed' THEN NEW.transformation_state_code IN ('approved', 'rejected')
    WHEN 'approved' THEN NEW.transformation_state_code IN ('started', 'cancelled')
    WHEN 'started' THEN NEW.transformation_state_code IN ('completed', 'cancelled')
    WHEN 'completed' THEN NEW.transformation_state_code IN ('verified', 'gap_detected')
    ELSE false
  END;

  IF NOT transition_allowed THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation state transition is not allowed';
  END IF;

  RETURN NEW;
END;
$$;

CREATE FUNCTION architecture_core.record_target_state_verification(
    requested_tenant_record_id uuid,
    requested_transformation_id uuid,
    requested_decision_request_id uuid,
    requested_effective_at timestamptz,
    requested_decision_actor_ref text,
    requested_decision_reason_text text,
    requested_evidence_record_id uuid,
    requested_verification_outcome_code text
)
RETURNS TABLE (
    transformation_history_record_id uuid,
    architecture_transformation_id uuid,
    verification_outcome_code text,
    outbox_event_id uuid,
    decision_request_id uuid,
    verification_recorded_at timestamptz,
    verification_replayed boolean,
    next_action text
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  existing_history_id uuid;
  existing_transformation_id uuid;
  existing_state_code text;
  existing_effective_at timestamptz;
  existing_actor_ref text;
  existing_reason_text text;
  existing_evidence_id uuid;
  existing_recorded_at timestamptz;
  existing_event_id uuid;
  previous_sequence_number integer;
  previous_state_code text;
  previous_effective_at timestamptz;
  inserted_history_id uuid;
  inserted_recorded_at timestamptz;
  inserted_event_id uuid;
BEGIN
  IF requested_tenant_record_id IS NULL
     OR requested_transformation_id IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_effective_at IS NULL
     OR requested_decision_actor_ref IS NULL
     OR requested_decision_reason_text IS NULL
     OR requested_evidence_record_id IS NULL
     OR requested_verification_outcome_code IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant, transformation, decision, time, actor, reason, evidence, and verification outcome are required';
  END IF;

  IF uuid_extract_version(requested_transformation_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR uuid_extract_version(requested_evidence_record_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state verification identifiers must be UUIDv7';
  END IF;

  IF requested_verification_outcome_code NOT IN ('verified', 'gap_detected') THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verification outcome must be verified or gap_detected';
  END IF;

  IF length(btrim(requested_decision_actor_ref)) NOT BETWEEN 1 AND 2048
     OR length(btrim(requested_decision_reason_text)) NOT BETWEEN 1 AND 4096 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verification actor and reason must be non-empty and bounded';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  -- Fast exact-replay path before taking the aggregate lock.
  SELECT
      history_record.transformation_history_record_id,
      history_record.architecture_transformation_id,
      history_record.transformation_state_code,
      history_record.effective_at,
      history_record.decision_actor_ref,
      history_record.decision_reason_text,
      history_record.evidence_record_id,
      history_record.recorded_at
    INTO
      existing_history_id,
      existing_transformation_id,
      existing_state_code,
      existing_effective_at,
      existing_actor_ref,
      existing_reason_text,
      existing_evidence_id,
      existing_recorded_at
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.decision_request_id = requested_decision_request_id;

  IF existing_history_id IS NOT NULL THEN
    IF existing_transformation_id IS DISTINCT FROM requested_transformation_id
       OR existing_state_code IS DISTINCT FROM requested_verification_outcome_code
       OR existing_effective_at IS DISTINCT FROM requested_effective_at
       OR existing_actor_ref IS DISTINCT FROM requested_decision_actor_ref
       OR existing_reason_text IS DISTINCT FROM requested_decision_reason_text
       OR existing_evidence_id IS DISTINCT FROM requested_evidence_record_id THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different verification meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = requested_tenant_record_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.transformation.verification_recorded.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'verification history exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_history_id,
      requested_transformation_id,
      existing_state_code,
      existing_event_id,
      requested_decision_request_id,
      existing_recorded_at,
      true,
      CASE existing_state_code
        WHEN 'verified' THEN 'monitor_target_state'
        ELSE 'replan_target_state'
      END::text;
    RETURN;
  END IF;

  -- Serialize every fresh verification decision on the authoritative aggregate.
  PERFORM 1
    FROM architecture_core.architecture_transformation AS transformation_record
   WHERE transformation_record.tenant_record_id = requested_tenant_record_id
     AND transformation_record.architecture_transformation_id =
         requested_transformation_id
     AND transformation_record.superseded_at IS NULL
     AND transformation_record.truth_status_code = 'authoritative'
   FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'authoritative transformation is unavailable for the verified tenant';
  END IF;

  -- Concurrent same-key delivery may have committed while this request waited.
  SELECT
      history_record.transformation_history_record_id,
      history_record.architecture_transformation_id,
      history_record.transformation_state_code,
      history_record.effective_at,
      history_record.decision_actor_ref,
      history_record.decision_reason_text,
      history_record.evidence_record_id,
      history_record.recorded_at
    INTO
      existing_history_id,
      existing_transformation_id,
      existing_state_code,
      existing_effective_at,
      existing_actor_ref,
      existing_reason_text,
      existing_evidence_id,
      existing_recorded_at
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.decision_request_id = requested_decision_request_id;

  IF existing_history_id IS NOT NULL THEN
    IF existing_transformation_id IS DISTINCT FROM requested_transformation_id
       OR existing_state_code IS DISTINCT FROM requested_verification_outcome_code
       OR existing_effective_at IS DISTINCT FROM requested_effective_at
       OR existing_actor_ref IS DISTINCT FROM requested_decision_actor_ref
       OR existing_reason_text IS DISTINCT FROM requested_decision_reason_text
       OR existing_evidence_id IS DISTINCT FROM requested_evidence_record_id THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different verification meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = requested_tenant_record_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.transformation.verification_recorded.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'verification history exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_history_id,
      requested_transformation_id,
      existing_state_code,
      existing_event_id,
      requested_decision_request_id,
      existing_recorded_at,
      true,
      CASE existing_state_code
        WHEN 'verified' THEN 'monitor_target_state'
        ELSE 'replan_target_state'
      END::text;
    RETURN;
  END IF;

  SELECT
      history_record.sequence_number,
      history_record.transformation_state_code,
      history_record.effective_at
    INTO
      previous_sequence_number,
      previous_state_code,
      previous_effective_at
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.architecture_transformation_id = requested_transformation_id
   ORDER BY history_record.sequence_number DESC
   LIMIT 1;

  IF previous_sequence_number IS NULL OR previous_state_code <> 'completed' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state verification requires completed transformation execution';
  END IF;

  IF requested_effective_at < previous_effective_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state verification cannot predate execution completion';
  END IF;

  INSERT INTO architecture_core.transformation_history_record (
      tenant_record_id,
      architecture_transformation_id,
      sequence_number,
      transformation_state_code,
      effective_at,
      decision_actor_ref,
      decision_reason_text,
      truth_status_code,
      evidence_record_id,
      decision_request_id
  ) VALUES (
      requested_tenant_record_id,
      requested_transformation_id,
      previous_sequence_number + 1,
      requested_verification_outcome_code,
      requested_effective_at,
      requested_decision_actor_ref,
      requested_decision_reason_text,
      'authoritative',
      requested_evidence_record_id,
      requested_decision_request_id
  )
  RETURNING
      transformation_history_record.transformation_history_record_id,
      transformation_history_record.recorded_at
    INTO inserted_history_id, inserted_recorded_at;

  INSERT INTO architecture_core.outbox_event (
      tenant_record_id,
      aggregate_object_id,
      architecture_transformation_id,
      event_type_code,
      event_payload_json,
      event_schema_version,
      decision_request_id
  ) VALUES (
      requested_tenant_record_id,
      NULL,
      requested_transformation_id,
      'org.contextualwisdomlab.ea.transformation.verification_recorded.v1',
      pg_catalog.jsonb_build_object(
          'architecture_transformation_id', requested_transformation_id,
          'transformation_history_record_id', inserted_history_id,
          'decision_request_id', requested_decision_request_id,
          'effective_at', requested_effective_at,
          'evidence_record_id', requested_evidence_record_id,
          'verification_outcome_code', requested_verification_outcome_code
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_history_id,
    requested_transformation_id,
    requested_verification_outcome_code,
    inserted_event_id,
    requested_decision_request_id,
    inserted_recorded_at,
    false,
    CASE requested_verification_outcome_code
      WHEN 'verified' THEN 'monitor_target_state'
      ELSE 'replan_target_state'
    END::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.record_target_state_verification(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid,
    text
)
FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM pg_catalog.pg_roles
       WHERE rolname = 'ea_runtime'
  ) THEN
    EXECUTE
      'GRANT EXECUTE ON FUNCTION architecture_core.record_target_state_verification('
      'uuid,uuid,uuid,timestamptz,text,text,uuid,text) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.record_target_state_verification(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid,
    text
) IS
'Purpose-bound human target-state verification command. The caller must already have verified Keyverse signature, issuer, audience, expiration, tenant and verification role. Verification is a distinct append-only authoritative history state accepted only after completed execution, cannot predate completion, uses an idempotent UUIDv7 decision request, and atomically emits privacy-minimized outbox evidence. verified returns monitor_target_state; gap_detected returns replan_target_state.';

COMMIT;
