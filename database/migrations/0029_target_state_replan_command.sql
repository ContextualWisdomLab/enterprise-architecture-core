BEGIN;

CREATE TABLE architecture_core.transformation_replan_record (
    tenant_record_id uuid NOT NULL,
    transformation_replan_record_id uuid NOT NULL DEFAULT uuidv7(),
    predecessor_architecture_transformation_id uuid NOT NULL,
    replacement_architecture_transformation_id uuid NOT NULL,
    decision_request_id uuid NOT NULL,
    effective_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    truth_status_code text NOT NULL,
    evidence_record_id uuid NOT NULL,
    CONSTRAINT transformation_replan_record_primary_key
        PRIMARY KEY (tenant_record_id, transformation_replan_record_id),
    CONSTRAINT transformation_replan_record_predecessor_foreign
        FOREIGN KEY (
            tenant_record_id,
            predecessor_architecture_transformation_id
        ) REFERENCES architecture_core.architecture_transformation (
            tenant_record_id,
            architecture_transformation_id
        ),
    CONSTRAINT transformation_replan_record_replacement_foreign
        FOREIGN KEY (
            tenant_record_id,
            replacement_architecture_transformation_id
        ) REFERENCES architecture_core.architecture_transformation (
            tenant_record_id,
            architecture_transformation_id
        ),
    CONSTRAINT transformation_replan_record_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT transformation_replan_record_uuid_version
        CHECK (uuid_extract_version(transformation_replan_record_id) = 7),
    CONSTRAINT transformation_replan_record_predecessor_uuid_version
        CHECK (
            uuid_extract_version(predecessor_architecture_transformation_id) = 7
        ),
    CONSTRAINT transformation_replan_record_replacement_uuid_version
        CHECK (
            uuid_extract_version(replacement_architecture_transformation_id) = 7
        ),
    CONSTRAINT transformation_replan_record_decision_uuid_version
        CHECK (uuid_extract_version(decision_request_id) = 7),
    CONSTRAINT transformation_replan_record_distinct_transformations
        CHECK (
            predecessor_architecture_transformation_id <>
            replacement_architecture_transformation_id
        ),
    CONSTRAINT transformation_replan_record_truth_authoritative
        CHECK (truth_status_code = 'authoritative'),
    CONSTRAINT transformation_replan_record_decision_unique
        UNIQUE (tenant_record_id, decision_request_id),
    CONSTRAINT transformation_replan_record_predecessor_unique
        UNIQUE (tenant_record_id, predecessor_architecture_transformation_id),
    CONSTRAINT transformation_replan_record_replacement_unique
        UNIQUE (tenant_record_id, replacement_architecture_transformation_id)
);

ALTER TABLE architecture_core.transformation_replan_record
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.transformation_replan_record
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.transformation_replan_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE FUNCTION architecture_core.reject_transformation_replan_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'transformation replan evidence is immutable';
END;
$$;

CREATE TRIGGER transformation_replan_record_update_guard
BEFORE UPDATE ON architecture_core.transformation_replan_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_transformation_replan_mutation();

CREATE TRIGGER transformation_replan_record_delete_guard
BEFORE DELETE ON architecture_core.transformation_replan_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_transformation_replan_mutation();

CREATE FUNCTION architecture_core.record_target_state_replan(
    requested_tenant_record_id uuid,
    requested_predecessor_transformation_id uuid,
    requested_replacement_transformation_id uuid,
    requested_decision_request_id uuid,
    requested_scenario_id uuid,
    requested_initiative_id uuid,
    requested_transformation_code text,
    requested_transformation_title text,
    requested_transformation_description text,
    requested_effective_at timestamptz,
    requested_decision_actor_ref text,
    requested_decision_reason_text text,
    requested_evidence_record_id uuid
)
RETURNS TABLE (
    transformation_replan_record_id uuid,
    predecessor_architecture_transformation_id uuid,
    replacement_architecture_transformation_id uuid,
    transformation_history_record_id uuid,
    outbox_event_id uuid,
    decision_request_id uuid,
    replan_recorded_at timestamptz,
    replan_replayed boolean,
    next_action text
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  existing_replan_id uuid;
  existing_predecessor_id uuid;
  existing_replacement_id uuid;
  existing_decision_id uuid;
  existing_effective_at timestamptz;
  existing_evidence_id uuid;
  existing_recorded_at timestamptz;
  existing_scenario_id uuid;
  existing_initiative_id uuid;
  existing_code text;
  existing_title text;
  existing_description text;
  existing_history_id uuid;
  existing_actor_ref text;
  existing_reason_text text;
  existing_event_id uuid;
  predecessor_superseded_at timestamptz;
  predecessor_truth_status_code text;
  previous_state_code text;
  previous_effective_at timestamptz;
  inserted_history_id uuid;
  inserted_replan_id uuid;
  inserted_recorded_at timestamptz;
  inserted_event_id uuid;
BEGIN
  IF requested_tenant_record_id IS NULL
     OR requested_predecessor_transformation_id IS NULL
     OR requested_replacement_transformation_id IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_scenario_id IS NULL
     OR requested_initiative_id IS NULL
     OR requested_transformation_code IS NULL
     OR requested_transformation_title IS NULL
     OR requested_transformation_description IS NULL
     OR requested_effective_at IS NULL
     OR requested_decision_actor_ref IS NULL
     OR requested_decision_reason_text IS NULL
     OR requested_evidence_record_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'replan tenant, predecessor, replacement, decision, scenario, initiative, transformation meaning, time, actor, reason, and evidence are required';
  END IF;

  IF uuid_extract_version(requested_predecessor_transformation_id) <> 7
     OR uuid_extract_version(requested_replacement_transformation_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR uuid_extract_version(requested_scenario_id) <> 7
     OR uuid_extract_version(requested_initiative_id) <> 7
     OR uuid_extract_version(requested_evidence_record_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state replan identifiers must be UUIDv7';
  END IF;

  IF requested_predecessor_transformation_id =
     requested_replacement_transformation_id THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state replan requires a distinct replacement transformation';
  END IF;

  IF requested_transformation_code !~
        '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
     OR length(requested_transformation_code) > 128
     OR length(btrim(requested_transformation_title)) NOT BETWEEN 1 AND 512
     OR length(btrim(requested_transformation_description)) NOT BETWEEN 1 AND 4096
     OR length(btrim(requested_decision_actor_ref)) NOT BETWEEN 1 AND 2048
     OR length(btrim(requested_decision_reason_text)) NOT BETWEEN 1 AND 4096 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state replan text fields are invalid or exceed their bounds';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  SELECT
      replan_record.transformation_replan_record_id,
      replan_record.predecessor_architecture_transformation_id,
      replan_record.replacement_architecture_transformation_id,
      replan_record.decision_request_id,
      replan_record.effective_at,
      replan_record.evidence_record_id,
      replan_record.recorded_at,
      replacement_record.architecture_scenario_id,
      replacement_record.remediation_initiative_id,
      replacement_record.transformation_code,
      replacement_record.transformation_title,
      replacement_record.transformation_description,
      history_record.transformation_history_record_id,
      history_record.decision_actor_ref,
      history_record.decision_reason_text
    INTO
      existing_replan_id,
      existing_predecessor_id,
      existing_replacement_id,
      existing_decision_id,
      existing_effective_at,
      existing_evidence_id,
      existing_recorded_at,
      existing_scenario_id,
      existing_initiative_id,
      existing_code,
      existing_title,
      existing_description,
      existing_history_id,
      existing_actor_ref,
      existing_reason_text
    FROM architecture_core.transformation_replan_record AS replan_record
    JOIN architecture_core.architecture_transformation AS replacement_record
      ON replacement_record.tenant_record_id = replan_record.tenant_record_id
     AND replacement_record.architecture_transformation_id =
         replan_record.replacement_architecture_transformation_id
    JOIN architecture_core.transformation_history_record AS history_record
      ON history_record.tenant_record_id = replan_record.tenant_record_id
     AND history_record.architecture_transformation_id =
         replan_record.replacement_architecture_transformation_id
     AND history_record.sequence_number = 1
   WHERE replan_record.tenant_record_id = requested_tenant_record_id
     AND replan_record.decision_request_id = requested_decision_request_id;

  IF existing_replan_id IS NOT NULL THEN
    IF existing_predecessor_id IS DISTINCT FROM
           requested_predecessor_transformation_id
       OR existing_replacement_id IS DISTINCT FROM
           requested_replacement_transformation_id
       OR existing_decision_id IS DISTINCT FROM requested_decision_request_id
       OR existing_effective_at IS DISTINCT FROM requested_effective_at
       OR existing_evidence_id IS DISTINCT FROM requested_evidence_record_id
       OR existing_scenario_id IS DISTINCT FROM requested_scenario_id
       OR existing_initiative_id IS DISTINCT FROM requested_initiative_id
       OR existing_code IS DISTINCT FROM requested_transformation_code
       OR existing_title IS DISTINCT FROM requested_transformation_title
       OR existing_description IS DISTINCT FROM requested_transformation_description
       OR existing_actor_ref IS DISTINCT FROM requested_decision_actor_ref
       OR existing_reason_text IS DISTINCT FROM requested_decision_reason_text THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different replan meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = requested_tenant_record_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.transformation.replanned.v1';

    IF existing_history_id IS NULL OR existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'replan evidence exists without proposed history or transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_replan_id,
      requested_predecessor_transformation_id,
      requested_replacement_transformation_id,
      existing_history_id,
      existing_event_id,
      requested_decision_request_id,
      existing_recorded_at,
      true,
      'approve_target_state'::text;
    RETURN;
  END IF;

  SELECT
      predecessor_record.superseded_at,
      predecessor_record.truth_status_code
    INTO predecessor_superseded_at, predecessor_truth_status_code
    FROM architecture_core.architecture_transformation AS predecessor_record
   WHERE predecessor_record.tenant_record_id = requested_tenant_record_id
     AND predecessor_record.architecture_transformation_id =
         requested_predecessor_transformation_id
   FOR UPDATE;

  IF predecessor_truth_status_code IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'predecessor transformation is unavailable for the verified tenant';
  END IF;

  -- A concurrent exact replay can become visible while this request waits for
  -- the predecessor aggregate lock. Re-enter the replay path before evaluating
  -- the now-superseded predecessor.
  SELECT
      replan_record.transformation_replan_record_id,
      replan_record.replacement_architecture_transformation_id,
      replan_record.recorded_at
    INTO existing_replan_id, existing_replacement_id, existing_recorded_at
    FROM architecture_core.transformation_replan_record AS replan_record
   WHERE replan_record.tenant_record_id = requested_tenant_record_id
     AND replan_record.decision_request_id = requested_decision_request_id;

  IF existing_replan_id IS NOT NULL THEN
    RETURN QUERY
    SELECT replayed.transformation_replan_record_id,
           replayed.predecessor_architecture_transformation_id,
           replayed.replacement_architecture_transformation_id,
           replayed.transformation_history_record_id,
           replayed.outbox_event_id,
           replayed.decision_request_id,
           replayed.replan_recorded_at,
           replayed.replan_replayed,
           replayed.next_action
      FROM architecture_core.record_target_state_replan(
          requested_tenant_record_id,
          requested_predecessor_transformation_id,
          requested_replacement_transformation_id,
          requested_decision_request_id,
          requested_scenario_id,
          requested_initiative_id,
          requested_transformation_code,
          requested_transformation_title,
          requested_transformation_description,
          requested_effective_at,
          requested_decision_actor_ref,
          requested_decision_reason_text,
          requested_evidence_record_id
      ) AS replayed;
    RETURN;
  END IF;

  IF predecessor_truth_status_code <> 'authoritative'
     OR predecessor_superseded_at IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'replanning requires an active authoritative predecessor';
  END IF;

  SELECT
      history_record.transformation_state_code,
      history_record.effective_at
    INTO previous_state_code, previous_effective_at
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.architecture_transformation_id =
         requested_predecessor_transformation_id
   ORDER BY history_record.sequence_number DESC
   LIMIT 1;

  IF previous_state_code IS DISTINCT FROM 'gap_detected' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state replanning requires a gap-detected predecessor';
  END IF;

  IF requested_effective_at < previous_effective_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state replanning cannot predate the detected gap';
  END IF;

  IF EXISTS (
      SELECT 1
        FROM architecture_core.architecture_transformation AS existing_replacement
       WHERE existing_replacement.tenant_record_id = requested_tenant_record_id
         AND existing_replacement.architecture_transformation_id =
             requested_replacement_transformation_id
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23505',
      MESSAGE = 'replacement transformation id already exists';
  END IF;

  UPDATE architecture_core.architecture_transformation
     SET superseded_at = clock_timestamp()
   WHERE tenant_record_id = requested_tenant_record_id
     AND architecture_transformation_id =
         requested_predecessor_transformation_id;

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
      truth_status_code,
      evidence_record_id
  ) VALUES (
      requested_tenant_record_id,
      requested_replacement_transformation_id,
      requested_scenario_id,
      requested_initiative_id,
      requested_transformation_code,
      requested_transformation_title,
      requested_transformation_description,
      requested_effective_at,
      NULL,
      'authoritative',
      requested_evidence_record_id
  );

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
      requested_replacement_transformation_id,
      1,
      'proposed',
      requested_effective_at,
      requested_decision_actor_ref,
      requested_decision_reason_text,
      'authoritative',
      requested_evidence_record_id,
      requested_decision_request_id
  )
  RETURNING transformation_history_record.transformation_history_record_id
    INTO inserted_history_id;

  INSERT INTO architecture_core.transformation_replan_record (
      tenant_record_id,
      predecessor_architecture_transformation_id,
      replacement_architecture_transformation_id,
      decision_request_id,
      effective_at,
      truth_status_code,
      evidence_record_id
  ) VALUES (
      requested_tenant_record_id,
      requested_predecessor_transformation_id,
      requested_replacement_transformation_id,
      requested_decision_request_id,
      requested_effective_at,
      'authoritative',
      requested_evidence_record_id
  )
  RETURNING
      transformation_replan_record.transformation_replan_record_id,
      transformation_replan_record.recorded_at
    INTO inserted_replan_id, inserted_recorded_at;

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
      requested_replacement_transformation_id,
      'org.contextualwisdomlab.ea.transformation.replanned.v1',
      pg_catalog.jsonb_build_object(
          'predecessor_architecture_transformation_id',
          requested_predecessor_transformation_id,
          'replacement_architecture_transformation_id',
          requested_replacement_transformation_id,
          'transformation_replan_record_id', inserted_replan_id,
          'transformation_history_record_id', inserted_history_id,
          'decision_request_id', requested_decision_request_id,
          'effective_at', requested_effective_at,
          'evidence_record_id', requested_evidence_record_id
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_replan_id,
    requested_predecessor_transformation_id,
    requested_replacement_transformation_id,
    inserted_history_id,
    inserted_event_id,
    requested_decision_request_id,
    inserted_recorded_at,
    false,
    'approve_target_state'::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.record_target_state_replan(
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
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
      'GRANT EXECUTE ON FUNCTION architecture_core.record_target_state_replan('
      'uuid,uuid,uuid,uuid,uuid,uuid,text,text,text,timestamptz,text,text,uuid) '
      'TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON TABLE architecture_core.transformation_replan_record IS
'Immutable tenant-scoped relationship proving that one terminal gap-detected architecture transformation was replaced by a distinct governed transformation. The predecessor history is never rewritten; superseded_at closes only its system-recorded visibility, while the replacement begins at proposed state and must pass the existing human approval command.';

COMMENT ON FUNCTION architecture_core.record_target_state_replan(
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    timestamptz,
    text,
    text,
    uuid
) IS
'Atomically supersedes one authoritative gap-detected predecessor in system time, creates a distinct evidence-backed authoritative replacement transformation in proposed state, records their immutable replan relationship, and emits a privacy-minimized transactional outbox event. Exact decision replay is idempotent; conflicting meaning fails closed.';

COMMIT;
