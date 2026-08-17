BEGIN;

CREATE TABLE architecture_core.transformation_schedule_record (
    tenant_record_id uuid NOT NULL,
    transformation_schedule_record_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_transformation_id uuid NOT NULL,
    initiative_milestone_id uuid NOT NULL,
    decision_request_id uuid NOT NULL,
    effective_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    decision_actor_ref text NOT NULL,
    decision_reason_text text NOT NULL,
    truth_status_code text NOT NULL,
    evidence_record_id uuid NOT NULL,
    CONSTRAINT transformation_schedule_record_primary_key
        PRIMARY KEY (tenant_record_id, transformation_schedule_record_id),
    CONSTRAINT transformation_schedule_record_transformation_foreign
        FOREIGN KEY (tenant_record_id, architecture_transformation_id)
        REFERENCES architecture_core.architecture_transformation
            (tenant_record_id, architecture_transformation_id),
    CONSTRAINT transformation_schedule_record_milestone_foreign
        FOREIGN KEY (tenant_record_id, initiative_milestone_id)
        REFERENCES architecture_core.initiative_milestone
            (tenant_record_id, initiative_milestone_id),
    CONSTRAINT transformation_schedule_record_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT transformation_schedule_record_uuid_version
        CHECK (uuid_extract_version(transformation_schedule_record_id) = 7),
    CONSTRAINT transformation_schedule_decision_uuid_version
        CHECK (uuid_extract_version(decision_request_id) = 7),
    CONSTRAINT transformation_schedule_actor_nonempty
        CHECK (length(btrim(decision_actor_ref)) BETWEEN 1 AND 2048),
    CONSTRAINT transformation_schedule_reason_nonempty
        CHECK (length(btrim(decision_reason_text)) BETWEEN 1 AND 4096),
    CONSTRAINT transformation_schedule_truth_authoritative
        CHECK (truth_status_code = 'authoritative'),
    CONSTRAINT transformation_schedule_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT transformation_schedule_decision_request_unique
        UNIQUE (tenant_record_id, decision_request_id)
);

ALTER TABLE architecture_core.transformation_schedule_record
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.transformation_schedule_record
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.transformation_schedule_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE UNIQUE INDEX transformation_schedule_active_index
    ON architecture_core.transformation_schedule_record
        (tenant_record_id, architecture_transformation_id)
    WHERE superseded_at IS NULL;

CREATE INDEX transformation_schedule_milestone_index
    ON architecture_core.transformation_schedule_record
        (tenant_record_id, initiative_milestone_id, effective_at)
    WHERE superseded_at IS NULL;

CREATE FUNCTION architecture_core.schedule_transformation(
    requested_tenant_record_id uuid,
    requested_transformation_id uuid,
    requested_decision_request_id uuid,
    requested_initiative_milestone_id uuid,
    requested_effective_at timestamptz,
    requested_decision_actor_ref text,
    requested_decision_reason_text text,
    requested_evidence_record_id uuid
)
RETURNS TABLE (
    transformation_schedule_record_id uuid,
    architecture_transformation_id uuid,
    initiative_milestone_id uuid,
    outbox_event_id uuid,
    decision_request_id uuid,
    milestone_target_at timestamptz,
    schedule_recorded_at timestamptz,
    schedule_replayed boolean,
    next_action text
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  existing_schedule_id uuid;
  existing_transformation_id uuid;
  existing_milestone_id uuid;
  existing_effective_at timestamptz;
  existing_actor_ref text;
  existing_reason_text text;
  existing_evidence_id uuid;
  existing_recorded_at timestamptz;
  existing_target_at timestamptz;
  existing_event_id uuid;
  transformation_initiative_id uuid;
  latest_state_code text;
  latest_effective_at timestamptz;
  selected_target_at timestamptz;
  inserted_schedule_id uuid;
  inserted_recorded_at timestamptz;
  inserted_event_id uuid;
BEGIN
  IF requested_tenant_record_id IS NULL
     OR requested_transformation_id IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_initiative_milestone_id IS NULL
     OR requested_effective_at IS NULL
     OR requested_decision_actor_ref IS NULL
     OR requested_decision_reason_text IS NULL
     OR requested_evidence_record_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant, transformation, decision, milestone, time, actor, reason, and evidence are required';
  END IF;

  IF uuid_extract_version(requested_transformation_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR uuid_extract_version(requested_initiative_milestone_id) <> 7
     OR uuid_extract_version(requested_evidence_record_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state schedule identifiers must be UUIDv7';
  END IF;

  IF length(btrim(requested_decision_actor_ref)) NOT BETWEEN 1 AND 2048
     OR length(btrim(requested_decision_reason_text)) NOT BETWEEN 1 AND 4096 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'schedule actor and reason must be non-empty and bounded';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  SELECT
      schedule_record.transformation_schedule_record_id,
      schedule_record.architecture_transformation_id,
      schedule_record.initiative_milestone_id,
      schedule_record.effective_at,
      schedule_record.decision_actor_ref,
      schedule_record.decision_reason_text,
      schedule_record.evidence_record_id,
      schedule_record.recorded_at,
      milestone_record.target_at
    INTO
      existing_schedule_id,
      existing_transformation_id,
      existing_milestone_id,
      existing_effective_at,
      existing_actor_ref,
      existing_reason_text,
      existing_evidence_id,
      existing_recorded_at,
      existing_target_at
    FROM architecture_core.transformation_schedule_record AS schedule_record
    JOIN architecture_core.initiative_milestone AS milestone_record
      ON milestone_record.tenant_record_id = schedule_record.tenant_record_id
     AND milestone_record.initiative_milestone_id = schedule_record.initiative_milestone_id
   WHERE schedule_record.tenant_record_id = requested_tenant_record_id
     AND schedule_record.decision_request_id = requested_decision_request_id;

  IF existing_schedule_id IS NOT NULL THEN
    IF existing_transformation_id IS DISTINCT FROM requested_transformation_id
       OR existing_milestone_id IS DISTINCT FROM requested_initiative_milestone_id
       OR existing_effective_at IS DISTINCT FROM requested_effective_at
       OR existing_actor_ref IS DISTINCT FROM requested_decision_actor_ref
       OR existing_reason_text IS DISTINCT FROM requested_decision_reason_text
       OR existing_evidence_id IS DISTINCT FROM requested_evidence_record_id THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different schedule meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = requested_tenant_record_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.transformation.scheduled.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'schedule record exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_schedule_id,
      requested_transformation_id,
      requested_initiative_milestone_id,
      existing_event_id,
      requested_decision_request_id,
      existing_target_at,
      existing_recorded_at,
      true,
      'start_transformation'::text;
    RETURN;
  END IF;

  SELECT transformation_record.remediation_initiative_id
    INTO transformation_initiative_id
    FROM architecture_core.architecture_transformation AS transformation_record
   WHERE transformation_record.tenant_record_id = requested_tenant_record_id
     AND transformation_record.architecture_transformation_id = requested_transformation_id
     AND transformation_record.superseded_at IS NULL
     AND transformation_record.truth_status_code = 'authoritative'
   FOR UPDATE;

  IF transformation_initiative_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'authoritative transformation is unavailable for the verified tenant';
  END IF;

  SELECT
      history_record.transformation_state_code,
      history_record.effective_at
    INTO latest_state_code, latest_effective_at
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.architecture_transformation_id = requested_transformation_id
   ORDER BY history_record.sequence_number DESC
   LIMIT 1;

  IF latest_state_code IS DISTINCT FROM 'approved' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state scheduling requires the current transformation state to be approved';
  END IF;

  IF requested_effective_at < latest_effective_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state scheduling cannot move backward in effective time';
  END IF;

  SELECT milestone_record.target_at
    INTO selected_target_at
    FROM architecture_core.initiative_milestone AS milestone_record
   WHERE milestone_record.tenant_record_id = requested_tenant_record_id
     AND milestone_record.initiative_milestone_id = requested_initiative_milestone_id
     AND milestone_record.remediation_initiative_id = transformation_initiative_id
     AND milestone_record.superseded_at IS NULL
     AND milestone_record.truth_status_code = 'authoritative'
     AND milestone_record.valid_from <= requested_effective_at
     AND (
         milestone_record.valid_to IS NULL
         OR requested_effective_at < milestone_record.valid_to
     )
   FOR SHARE;

  IF selected_target_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'authoritative milestone does not belong to the transformation remediation initiative';
  END IF;

  IF selected_target_at < requested_effective_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state scheduling cannot bind an already-past milestone';
  END IF;

  INSERT INTO architecture_core.transformation_schedule_record (
      tenant_record_id,
      architecture_transformation_id,
      initiative_milestone_id,
      decision_request_id,
      effective_at,
      decision_actor_ref,
      decision_reason_text,
      truth_status_code,
      evidence_record_id
  ) VALUES (
      requested_tenant_record_id,
      requested_transformation_id,
      requested_initiative_milestone_id,
      requested_decision_request_id,
      requested_effective_at,
      requested_decision_actor_ref,
      requested_decision_reason_text,
      'authoritative',
      requested_evidence_record_id
  )
  RETURNING
      transformation_schedule_record.transformation_schedule_record_id,
      transformation_schedule_record.recorded_at
    INTO inserted_schedule_id, inserted_recorded_at;

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
      'org.contextualwisdomlab.ea.transformation.scheduled.v1',
      pg_catalog.jsonb_build_object(
          'architecture_transformation_id', requested_transformation_id,
          'transformation_schedule_record_id', inserted_schedule_id,
          'initiative_milestone_id', requested_initiative_milestone_id,
          'decision_request_id', requested_decision_request_id,
          'effective_at', requested_effective_at,
          'milestone_target_at', selected_target_at,
          'evidence_record_id', requested_evidence_record_id
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_schedule_id,
    requested_transformation_id,
    requested_initiative_milestone_id,
    inserted_event_id,
    requested_decision_request_id,
    selected_target_at,
    inserted_recorded_at,
    false,
    'start_transformation'::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.schedule_transformation(
    uuid,
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
      'GRANT EXECUTE ON FUNCTION architecture_core.schedule_transformation('
      'uuid,uuid,uuid,uuid,timestamptz,text,text,uuid) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON TABLE architecture_core.transformation_schedule_record IS
'Append-preserving authoritative EA scheduling decision that binds one approved architecture transformation to an existing milestone of the same remediation initiative. The milestone remains the source of target date truth; this table records the governed binding, actor, reason, evidence, business-effective time, and system-recorded time.';

COMMENT ON FUNCTION architecture_core.schedule_transformation(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz,
    text,
    text,
    uuid
) IS
'Purpose-bound command that binds an approved authoritative EA transformation to an authoritative milestone of its remediation initiative. One UUIDv7 decision request is idempotent; exact replay returns the original schedule/outbox receipt, conflicting meaning is rejected, and the authoritative schedule record and privacy-minimized outbox event commit atomically.';

COMMIT;
