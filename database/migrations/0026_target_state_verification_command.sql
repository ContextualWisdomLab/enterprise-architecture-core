BEGIN;

CREATE TABLE architecture_core.transformation_verification_record (
    tenant_record_id uuid NOT NULL,
    transformation_verification_record_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_transformation_id uuid NOT NULL,
    verification_outcome_code text NOT NULL,
    effective_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    decision_actor_ref text NOT NULL,
    decision_reason_text text NOT NULL,
    evidence_record_id uuid NOT NULL,
    decision_request_id uuid NOT NULL,
    CONSTRAINT transformation_verification_record_primary_key
        PRIMARY KEY (tenant_record_id, transformation_verification_record_id),
    CONSTRAINT transformation_verification_record_transformation_foreign
        FOREIGN KEY (tenant_record_id, architecture_transformation_id)
        REFERENCES architecture_core.architecture_transformation
            (tenant_record_id, architecture_transformation_id),
    CONSTRAINT transformation_verification_record_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT transformation_verification_record_uuid_version
        CHECK (uuid_extract_version(transformation_verification_record_id) = 7),
    CONSTRAINT transformation_verification_decision_uuid_version
        CHECK (uuid_extract_version(decision_request_id) = 7),
    CONSTRAINT transformation_verification_outcome_allowed
        CHECK (verification_outcome_code IN ('verified', 'gap_detected')),
    CONSTRAINT transformation_verification_actor_nonempty
        CHECK (length(btrim(decision_actor_ref)) BETWEEN 1 AND 2048),
    CONSTRAINT transformation_verification_reason_nonempty
        CHECK (length(btrim(decision_reason_text)) BETWEEN 1 AND 4096),
    CONSTRAINT transformation_verification_transformation_unique
        UNIQUE (tenant_record_id, architecture_transformation_id),
    CONSTRAINT transformation_verification_decision_unique
        UNIQUE (tenant_record_id, decision_request_id)
);

ALTER TABLE architecture_core.transformation_verification_record
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.transformation_verification_record
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.transformation_verification_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX transformation_verification_effective_index
    ON architecture_core.transformation_verification_record
        (
            tenant_record_id,
            architecture_transformation_id,
            effective_at DESC,
            recorded_at DESC
        );

CREATE FUNCTION architecture_core.reject_transformation_verification_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'target-state verification evidence is append-only';
END;
$$;

CREATE TRIGGER transformation_verification_immutable_guard
BEFORE UPDATE OR DELETE
ON architecture_core.transformation_verification_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_transformation_verification_mutation();

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
    transformation_verification_record_id uuid,
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
  existing_verification_id uuid;
  existing_transformation_id uuid;
  existing_outcome_code text;
  existing_effective_at timestamptz;
  existing_actor_ref text;
  existing_reason_text text;
  existing_evidence_id uuid;
  existing_recorded_at timestamptz;
  existing_event_id uuid;
  existing_transformation_verification_id uuid;
  completed_effective_at timestamptz;
  latest_state_code text;
  inserted_verification_id uuid;
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

  SELECT
      verification_record.transformation_verification_record_id,
      verification_record.architecture_transformation_id,
      verification_record.verification_outcome_code,
      verification_record.effective_at,
      verification_record.decision_actor_ref,
      verification_record.decision_reason_text,
      verification_record.evidence_record_id,
      verification_record.recorded_at
    INTO
      existing_verification_id,
      existing_transformation_id,
      existing_outcome_code,
      existing_effective_at,
      existing_actor_ref,
      existing_reason_text,
      existing_evidence_id,
      existing_recorded_at
    FROM architecture_core.transformation_verification_record AS verification_record
   WHERE verification_record.tenant_record_id = requested_tenant_record_id
     AND verification_record.decision_request_id = requested_decision_request_id;

  IF existing_verification_id IS NOT NULL THEN
    IF existing_transformation_id IS DISTINCT FROM requested_transformation_id
       OR existing_outcome_code IS DISTINCT FROM requested_verification_outcome_code
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
        MESSAGE = 'verification evidence exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_verification_id,
      requested_transformation_id,
      existing_outcome_code,
      existing_event_id,
      requested_decision_request_id,
      existing_recorded_at,
      true,
      CASE existing_outcome_code
        WHEN 'verified' THEN 'monitor_target_state'
        ELSE 'replan_target_state'
      END::text;
    RETURN;
  END IF;

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

  -- Recheck after serializing the aggregate so concurrent exact replay returns
  -- one immutable receipt instead of racing the unique decision constraint.
  SELECT
      verification_record.transformation_verification_record_id,
      verification_record.architecture_transformation_id,
      verification_record.verification_outcome_code,
      verification_record.effective_at,
      verification_record.decision_actor_ref,
      verification_record.decision_reason_text,
      verification_record.evidence_record_id,
      verification_record.recorded_at
    INTO
      existing_verification_id,
      existing_transformation_id,
      existing_outcome_code,
      existing_effective_at,
      existing_actor_ref,
      existing_reason_text,
      existing_evidence_id,
      existing_recorded_at
    FROM architecture_core.transformation_verification_record AS verification_record
   WHERE verification_record.tenant_record_id = requested_tenant_record_id
     AND verification_record.decision_request_id = requested_decision_request_id;

  IF existing_verification_id IS NOT NULL THEN
    IF existing_transformation_id IS DISTINCT FROM requested_transformation_id
       OR existing_outcome_code IS DISTINCT FROM requested_verification_outcome_code
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
        MESSAGE = 'verification evidence exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_verification_id,
      requested_transformation_id,
      existing_outcome_code,
      existing_event_id,
      requested_decision_request_id,
      existing_recorded_at,
      true,
      CASE existing_outcome_code
        WHEN 'verified' THEN 'monitor_target_state'
        ELSE 'replan_target_state'
      END::text;
    RETURN;
  END IF;

  SELECT verification_record.transformation_verification_record_id
    INTO existing_transformation_verification_id
    FROM architecture_core.transformation_verification_record AS verification_record
   WHERE verification_record.tenant_record_id = requested_tenant_record_id
     AND verification_record.architecture_transformation_id =
         requested_transformation_id;

  IF existing_transformation_verification_id IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23505',
      MESSAGE = 'completed transformation already has target-state verification evidence';
  END IF;

  SELECT
      history_record.transformation_state_code,
      history_record.effective_at
    INTO latest_state_code, completed_effective_at
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.architecture_transformation_id = requested_transformation_id
   ORDER BY history_record.sequence_number DESC
   LIMIT 1;

  IF latest_state_code IS DISTINCT FROM 'completed' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state verification requires completed transformation execution';
  END IF;

  IF requested_effective_at < completed_effective_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state verification cannot predate execution completion';
  END IF;

  INSERT INTO architecture_core.transformation_verification_record (
      tenant_record_id,
      architecture_transformation_id,
      verification_outcome_code,
      effective_at,
      decision_actor_ref,
      decision_reason_text,
      evidence_record_id,
      decision_request_id
  ) VALUES (
      requested_tenant_record_id,
      requested_transformation_id,
      requested_verification_outcome_code,
      requested_effective_at,
      requested_decision_actor_ref,
      requested_decision_reason_text,
      requested_evidence_record_id,
      requested_decision_request_id
  )
  RETURNING
      transformation_verification_record.transformation_verification_record_id,
      transformation_verification_record.recorded_at
    INTO inserted_verification_id, inserted_recorded_at;

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
          'transformation_verification_record_id', inserted_verification_id,
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
    inserted_verification_id,
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
ON TABLE architecture_core.transformation_verification_record
FROM PUBLIC;

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
      'GRANT SELECT ON TABLE architecture_core.transformation_verification_record '
      'TO ea_runtime';
    EXECUTE
      'GRANT EXECUTE ON FUNCTION architecture_core.record_target_state_verification('
      'uuid,uuid,uuid,timestamptz,text,text,uuid,text) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON TABLE architecture_core.transformation_verification_record IS
'Immutable tenant-scoped human verification evidence for one completed EA transformation. Execution completion and target-state verification remain distinct: verified confirms the approved target state with explicit evidence, while gap_detected requires replanning. Foreign product facts are referenced as evidence and never promoted or mutated by this table.';

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
'Purpose-bound human target-state verification command. The caller must already have verified Keyverse signature, issuer, audience, expiration, tenant and verification role. Verification is accepted only after authoritative completed execution, cannot predate completion, is append-only and one-per-transformation, uses an idempotent UUIDv7 decision request, and atomically emits privacy-minimized outbox evidence. verified returns monitor_target_state; gap_detected returns replan_target_state.';

COMMIT;
