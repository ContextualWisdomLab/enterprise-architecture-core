BEGIN;

-- Transformation decisions are command aggregates in their own right. Earlier
-- outbox rows were architecture-object aggregates only; retain that contract for
-- existing rows while allowing exactly one typed transformation aggregate for
-- governed execution events.
ALTER TABLE architecture_core.outbox_event
    ALTER COLUMN aggregate_object_id DROP NOT NULL,
    ADD COLUMN architecture_transformation_id uuid,
    ADD COLUMN decision_request_id uuid,
    ADD CONSTRAINT outbox_event_transformation_foreign
        FOREIGN KEY (tenant_record_id, architecture_transformation_id)
        REFERENCES architecture_core.architecture_transformation
            (tenant_record_id, architecture_transformation_id),
    ADD CONSTRAINT outbox_event_aggregate_exactly_one
        CHECK (
            (aggregate_object_id IS NOT NULL)::integer
            + (architecture_transformation_id IS NOT NULL)::integer
            = 1
        ),
    ADD CONSTRAINT outbox_event_decision_request_uuid_version
        CHECK (
            decision_request_id IS NULL
            OR uuid_extract_version(decision_request_id) = 7
        ),
    ADD CONSTRAINT outbox_event_decision_request_unique
        UNIQUE (tenant_record_id, decision_request_id);

ALTER TABLE architecture_core.transformation_history_record
    ADD COLUMN decision_request_id uuid,
    ADD CONSTRAINT transformation_history_decision_request_uuid_version
        CHECK (
            decision_request_id IS NULL
            OR uuid_extract_version(decision_request_id) = 7
        ),
    ADD CONSTRAINT transformation_history_decision_request_unique
        UNIQUE (tenant_record_id, decision_request_id);

CREATE INDEX outbox_event_transformation_index
    ON architecture_core.outbox_event
        (tenant_record_id, architecture_transformation_id, recorded_at)
    WHERE architecture_transformation_id IS NOT NULL;

CREATE FUNCTION architecture_core.approve_target_state(
    requested_tenant_record_id uuid,
    requested_transformation_id uuid,
    requested_decision_request_id uuid,
    requested_effective_at timestamptz,
    requested_decision_actor_ref text,
    requested_decision_reason_text text,
    requested_evidence_record_id uuid
)
RETURNS TABLE (
    transformation_history_record_id uuid,
    transformation_state_code text,
    outbox_event_id uuid,
    decision_request_id uuid,
    approval_recorded_at timestamptz,
    replayed boolean,
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
     OR requested_evidence_record_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant, transformation, decision, time, actor, reason, and evidence are required';
  END IF;

  IF uuid_extract_version(requested_transformation_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR uuid_extract_version(requested_evidence_record_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state approval identifiers must be UUIDv7';
  END IF;

  IF length(btrim(requested_decision_actor_ref)) NOT BETWEEN 1 AND 2048
     OR length(btrim(requested_decision_reason_text)) NOT BETWEEN 1 AND 4096 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'approval actor and reason must be non-empty and bounded';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  SELECT
      history_record.transformation_history_record_id,
      history_record.architecture_transformation_id,
      history_record.effective_at,
      history_record.decision_actor_ref,
      history_record.decision_reason_text,
      history_record.evidence_record_id,
      history_record.recorded_at
    INTO
      existing_history_id,
      existing_transformation_id,
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
       OR existing_effective_at IS DISTINCT FROM requested_effective_at
       OR existing_actor_ref IS DISTINCT FROM requested_decision_actor_ref
       OR existing_reason_text IS DISTINCT FROM requested_decision_reason_text
       OR existing_evidence_id IS DISTINCT FROM requested_evidence_record_id THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different approval meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = requested_tenant_record_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.transformation.approved.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'approval history exists without its transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_history_id,
      'approved'::text,
      existing_event_id,
      requested_decision_request_id,
      existing_recorded_at,
      true,
      'schedule_transformation'::text;
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

  IF previous_sequence_number IS NULL OR previous_state_code <> 'proposed' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state approval requires the current transformation state to be proposed';
  END IF;

  IF requested_effective_at < previous_effective_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state approval cannot move backward in effective time';
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
      'approved',
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
      'org.contextualwisdomlab.ea.transformation.approved.v1',
      pg_catalog.jsonb_build_object(
          'architecture_transformation_id', requested_transformation_id,
          'transformation_history_record_id', inserted_history_id,
          'decision_request_id', requested_decision_request_id,
          'effective_at', requested_effective_at,
          'evidence_record_id', requested_evidence_record_id,
          'transformation_state_code', 'approved'
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_history_id,
    'approved'::text,
    inserted_event_id,
    requested_decision_request_id,
    inserted_recorded_at,
    false,
    'schedule_transformation'::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.approve_target_state(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
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
      'GRANT EXECUTE ON FUNCTION architecture_core.approve_target_state('
      'uuid,uuid,uuid,timestamptz,text,text,uuid) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.approve_target_state(
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
) IS
'Purpose-bound human approval command for a proposed authoritative EA transformation. The caller must already have verified Keyverse signature, issuer, audience, expiration, tenant and approval role. One UUIDv7 decision request is idempotent: an exact replay returns the original history/outbox receipt, while conflicting meaning is rejected. The authoritative history append and privacy-minimized transformation outbox event commit in the same transaction.';

COMMIT;
