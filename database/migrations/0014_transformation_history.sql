BEGIN;

CREATE TABLE architecture_core.architecture_transformation (
    tenant_record_id uuid NOT NULL,
    architecture_transformation_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_scenario_id uuid NOT NULL,
    remediation_initiative_id uuid NOT NULL,
    transformation_code text NOT NULL,
    transformation_title text NOT NULL,
    transformation_description text,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT architecture_transformation_primary_key
        PRIMARY KEY (tenant_record_id, architecture_transformation_id),
    CONSTRAINT architecture_transformation_scenario_foreign
        FOREIGN KEY (tenant_record_id, architecture_scenario_id)
        REFERENCES architecture_core.architecture_scenario
            (tenant_record_id, architecture_scenario_id),
    CONSTRAINT architecture_transformation_initiative_foreign
        FOREIGN KEY (tenant_record_id, remediation_initiative_id)
        REFERENCES architecture_core.remediation_initiative
            (tenant_record_id, remediation_initiative_id),
    CONSTRAINT architecture_transformation_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT architecture_transformation_uuid_version
        CHECK (uuid_extract_version(architecture_transformation_id) = 7),
    CONSTRAINT architecture_transformation_code_format
        CHECK (transformation_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT architecture_transformation_title_nonempty
        CHECK (length(btrim(transformation_title)) > 0),
    CONSTRAINT architecture_transformation_description_length
        CHECK (
            transformation_description IS NULL
            OR length(transformation_description) BETWEEN 1 AND 4096
        ),
    CONSTRAINT architecture_transformation_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT architecture_transformation_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT architecture_transformation_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT architecture_transformation_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT architecture_transformation_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            transformation_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE TABLE architecture_core.transformation_history_record (
    tenant_record_id uuid NOT NULL,
    transformation_history_record_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_transformation_id uuid NOT NULL,
    sequence_number integer NOT NULL,
    transformation_state_code text NOT NULL,
    effective_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    decision_actor_ref text NOT NULL,
    decision_reason_text text NOT NULL,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT transformation_history_record_primary_key
        PRIMARY KEY (tenant_record_id, transformation_history_record_id),
    CONSTRAINT transformation_history_record_transformation_foreign
        FOREIGN KEY (tenant_record_id, architecture_transformation_id)
        REFERENCES architecture_core.architecture_transformation
            (tenant_record_id, architecture_transformation_id),
    CONSTRAINT transformation_history_record_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT transformation_history_record_uuid_version
        CHECK (uuid_extract_version(transformation_history_record_id) = 7),
    CONSTRAINT transformation_history_record_sequence_positive
        CHECK (sequence_number > 0),
    CONSTRAINT transformation_history_record_state_allowed
        CHECK (
            transformation_state_code IN (
                'proposed',
                'approved',
                'started',
                'completed',
                'cancelled',
                'rejected'
            )
        ),
    CONSTRAINT transformation_history_record_actor_nonempty
        CHECK (
            length(btrim(decision_actor_ref)) BETWEEN 1 AND 2048
        ),
    CONSTRAINT transformation_history_record_reason_nonempty
        CHECK (
            length(btrim(decision_reason_text)) BETWEEN 1 AND 4096
        ),
    CONSTRAINT transformation_history_record_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT transformation_history_record_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT transformation_history_record_decision_authority
        CHECK (
            transformation_state_code NOT IN (
                'approved', 'cancelled', 'rejected'
            )
            OR truth_status_code = 'authoritative'
        ),
    CONSTRAINT transformation_history_record_execution_truth
        CHECK (
            transformation_state_code NOT IN ('started', 'completed')
            OR truth_status_code IN ('authoritative', 'observed')
        ),
    CONSTRAINT transformation_history_record_recording_chronology
        CHECK (recorded_at >= effective_at),
    CONSTRAINT transformation_history_record_sequence_unique
        UNIQUE (
            tenant_record_id,
            architecture_transformation_id,
            sequence_number
        )
);

ALTER TABLE architecture_core.architecture_transformation
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.architecture_transformation
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.architecture_transformation
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.transformation_history_record
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.transformation_history_record
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.transformation_history_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX architecture_transformation_scenario_index
    ON architecture_core.architecture_transformation
        (tenant_record_id, architecture_scenario_id, remediation_initiative_id)
    WHERE superseded_at IS NULL;

CREATE INDEX transformation_history_projection_index
    ON architecture_core.transformation_history_record
        (
            tenant_record_id,
            architecture_transformation_id,
            effective_at DESC,
            recorded_at DESC,
            sequence_number DESC
        );

CREATE FUNCTION architecture_core.validate_architecture_transformation_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  scenario_valid_from timestamptz;
  scenario_valid_to timestamptz;
  scenario_target_valid_at timestamptz;
  scenario_superseded_at timestamptz;
  scenario_truth_status_code text;
  initiative_valid_from timestamptz;
  initiative_valid_to timestamptz;
  initiative_superseded_at timestamptz;
  initiative_truth_status_code text;
  baseline_exists boolean;
BEGIN
  SELECT
      valid_from,
      valid_to,
      target_valid_at,
      superseded_at,
      truth_status_code
    INTO
      scenario_valid_from,
      scenario_valid_to,
      scenario_target_valid_at,
      scenario_superseded_at,
      scenario_truth_status_code
    FROM architecture_core.architecture_scenario
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_scenario_id = NEW.architecture_scenario_id;

  SELECT
      valid_from,
      valid_to,
      superseded_at,
      truth_status_code
    INTO
      initiative_valid_from,
      initiative_valid_to,
      initiative_superseded_at,
      initiative_truth_status_code
    FROM architecture_core.remediation_initiative
   WHERE tenant_record_id = NEW.tenant_record_id
     AND remediation_initiative_id = NEW.remediation_initiative_id;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.scenario_baseline AS scenario_baseline
       WHERE scenario_baseline.tenant_record_id = NEW.tenant_record_id
         AND scenario_baseline.architecture_scenario_id =
             NEW.architecture_scenario_id
  ) INTO baseline_exists;

  IF scenario_valid_from IS NOT NULL AND NOT baseline_exists THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation requires an immutable scenario baseline';
  END IF;

  IF scenario_valid_from IS NOT NULL
     AND (
        scenario_superseded_at IS NOT NULL
        OR scenario_truth_status_code IN ('superseded', 'rejected')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation cannot target an inactive scenario';
  END IF;

  IF initiative_valid_from IS NOT NULL
     AND (
        initiative_superseded_at IS NOT NULL
        OR initiative_truth_status_code IN ('superseded', 'rejected')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation cannot use an inactive remediation initiative';
  END IF;

  IF scenario_valid_from IS NOT NULL
     AND NOT (
        tstzrange(NEW.valid_from, NEW.valid_to, '[)')
        <@ tstzrange(scenario_valid_from, scenario_valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation validity exceeds scenario validity';
  END IF;

  IF initiative_valid_from IS NOT NULL
     AND NOT (
        tstzrange(NEW.valid_from, NEW.valid_to, '[)')
        <@ tstzrange(initiative_valid_from, initiative_valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation validity exceeds initiative validity';
  END IF;

  IF scenario_target_valid_at IS NOT NULL
     AND NOT (
        scenario_target_valid_at
        <@ tstzrange(NEW.valid_from, NEW.valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'scenario target lies outside transformation validity';
  END IF;

  RETURN NEW;
END;
$$;

CREATE FUNCTION architecture_core.reject_transformation_meaning_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'transformation meaning is immutable; supersede and append a new fact';
END;
$$;

CREATE FUNCTION architecture_core.validate_transformation_supersession()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.superseded_at IS NOT NULL
     AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'transformation supersession time is immutable once recorded';
  END IF;

  RETURN NEW;
END;
$$;

CREATE FUNCTION architecture_core.validate_transformation_history_semantics()
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

CREATE FUNCTION architecture_core.reject_transformation_history_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'transformation history is append-only';
END;
$$;

CREATE TRIGGER architecture_transformation_semantic_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    architecture_scenario_id,
    remediation_initiative_id,
    valid_from,
    valid_to
ON architecture_core.architecture_transformation
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_architecture_transformation_semantics();

CREATE TRIGGER architecture_transformation_immutable_guard
BEFORE UPDATE OF
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
ON architecture_core.architecture_transformation
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_transformation_meaning_mutation();

CREATE TRIGGER architecture_transformation_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.architecture_transformation
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_transformation_supersession();

CREATE TRIGGER transformation_history_record_semantic_guard
BEFORE INSERT ON architecture_core.transformation_history_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_transformation_history_semantics();

CREATE TRIGGER transformation_history_record_update_guard
BEFORE UPDATE ON architecture_core.transformation_history_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_transformation_history_mutation();

CREATE TRIGGER transformation_history_record_delete_guard
BEFORE DELETE ON architecture_core.transformation_history_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_transformation_history_mutation();

CREATE FUNCTION architecture_core.project_transformation_state(
    requested_transformation_id uuid,
    requested_valid_at timestamptz,
    requested_recorded_at timestamptz
)
RETURNS TABLE (
    transformation_state_code text,
    sequence_number integer,
    effective_at timestamptz,
    recorded_at timestamptz,
    decision_actor_ref text,
    decision_reason_text text,
    truth_status_code text,
    evidence_record_id uuid
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    history_record.transformation_state_code,
    history_record.sequence_number,
    history_record.effective_at,
    history_record.recorded_at,
    history_record.decision_actor_ref,
    history_record.decision_reason_text,
    history_record.truth_status_code,
    history_record.evidence_record_id
    FROM architecture_core.architecture_transformation AS transformation_record
    JOIN architecture_core.transformation_history_record AS history_record
      ON history_record.tenant_record_id = transformation_record.tenant_record_id
     AND history_record.architecture_transformation_id =
         transformation_record.architecture_transformation_id
   WHERE transformation_record.tenant_record_id =
         architecture_core.current_tenant_id()
     AND transformation_record.architecture_transformation_id =
         requested_transformation_id
     AND transformation_record.valid_from <= requested_valid_at
     AND (
        transformation_record.valid_to IS NULL
        OR transformation_record.valid_to > requested_valid_at
     )
     AND transformation_record.recorded_at <= requested_recorded_at
     AND (
        transformation_record.superseded_at IS NULL
        OR transformation_record.superseded_at > requested_recorded_at
     )
     AND history_record.effective_at <= requested_valid_at
     AND history_record.recorded_at <= requested_recorded_at
   ORDER BY
     history_record.effective_at DESC,
     history_record.sequence_number DESC
   LIMIT 1;
$$;

COMMIT;
