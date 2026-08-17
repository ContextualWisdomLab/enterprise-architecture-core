BEGIN;

CREATE TABLE architecture_core.architecture_scenario (
    tenant_record_id uuid NOT NULL,
    architecture_scenario_id uuid NOT NULL DEFAULT uuidv7(),
    scenario_code text NOT NULL,
    scenario_title text NOT NULL,
    scenario_description text,
    target_valid_at timestamptz NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT architecture_scenario_primary_key
        PRIMARY KEY (tenant_record_id, architecture_scenario_id),
    CONSTRAINT architecture_scenario_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT architecture_scenario_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT architecture_scenario_uuid_version
        CHECK (uuid_extract_version(architecture_scenario_id) = 7),
    CONSTRAINT architecture_scenario_code_format
        CHECK (scenario_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT architecture_scenario_title_nonempty
        CHECK (length(btrim(scenario_title)) > 0),
    CONSTRAINT architecture_scenario_description_length
        CHECK (
            scenario_description IS NULL
            OR length(scenario_description) BETWEEN 1 AND 4096
        ),
    CONSTRAINT architecture_scenario_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT architecture_scenario_target_interval
        CHECK (
            target_valid_at >= valid_from
            AND (valid_to IS NULL OR target_valid_at < valid_to)
        ),
    CONSTRAINT architecture_scenario_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT architecture_scenario_truth_allowed
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
    CONSTRAINT architecture_scenario_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT architecture_scenario_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            scenario_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE TABLE architecture_core.scenario_baseline (
    tenant_record_id uuid NOT NULL,
    scenario_baseline_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_scenario_id uuid NOT NULL,
    baseline_valid_at timestamptz NOT NULL,
    baseline_recorded_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT scenario_baseline_primary_key
        PRIMARY KEY (tenant_record_id, scenario_baseline_id),
    CONSTRAINT scenario_baseline_scenario_foreign
        FOREIGN KEY (tenant_record_id, architecture_scenario_id)
        REFERENCES architecture_core.architecture_scenario
            (tenant_record_id, architecture_scenario_id),
    CONSTRAINT scenario_baseline_uuid_version
        CHECK (uuid_extract_version(scenario_baseline_id) = 7),
    CONSTRAINT scenario_baseline_recording_chronology
        CHECK (baseline_recorded_at <= recorded_at),
    CONSTRAINT scenario_baseline_scenario_unique
        UNIQUE (tenant_record_id, architecture_scenario_id)
);

CREATE TABLE architecture_core.scenario_object_delta (
    tenant_record_id uuid NOT NULL,
    scenario_object_delta_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_scenario_id uuid NOT NULL,
    sequence_number integer NOT NULL,
    architecture_object_id uuid NOT NULL,
    desired_presence_code text NOT NULL,
    effective_from timestamptz NOT NULL,
    effective_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT scenario_object_delta_primary_key
        PRIMARY KEY (tenant_record_id, scenario_object_delta_id),
    CONSTRAINT scenario_object_delta_scenario_foreign
        FOREIGN KEY (tenant_record_id, architecture_scenario_id)
        REFERENCES architecture_core.architecture_scenario
            (tenant_record_id, architecture_scenario_id),
    CONSTRAINT scenario_object_delta_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT scenario_object_delta_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT scenario_object_delta_uuid_version
        CHECK (uuid_extract_version(scenario_object_delta_id) = 7),
    CONSTRAINT scenario_object_delta_sequence_positive
        CHECK (sequence_number > 0),
    CONSTRAINT scenario_object_delta_presence_allowed
        CHECK (desired_presence_code IN ('present', 'absent')),
    CONSTRAINT scenario_object_delta_effective_interval
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT scenario_object_delta_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT scenario_object_delta_truth_allowed
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
    CONSTRAINT scenario_object_delta_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT scenario_object_delta_sequence_unique
        UNIQUE (tenant_record_id, architecture_scenario_id, sequence_number)
);

CREATE FUNCTION architecture_core.validate_scenario_baseline_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  scenario_target_valid_at timestamptz;
  scenario_superseded_at timestamptz;
  scenario_truth_status_code text;
BEGIN
  SELECT target_valid_at, superseded_at, truth_status_code
    INTO scenario_target_valid_at, scenario_superseded_at,
         scenario_truth_status_code
    FROM architecture_core.architecture_scenario
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_scenario_id = NEW.architecture_scenario_id;

  IF scenario_target_valid_at IS NOT NULL
     AND NEW.baseline_valid_at > scenario_target_valid_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'scenario baseline valid time exceeds target valid time';
  END IF;

  IF scenario_target_valid_at IS NOT NULL
     AND (
        scenario_superseded_at IS NOT NULL
        OR scenario_truth_status_code IN ('superseded', 'rejected')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'scenario baseline cannot be attached to an inactive scenario';
  END IF;

  RETURN NEW;
END;
$$;

CREATE FUNCTION architecture_core.validate_scenario_delta_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  scenario_target_valid_at timestamptz;
  scenario_superseded_at timestamptz;
  scenario_truth_status_code text;
  baseline_exists boolean;
BEGIN
  SELECT target_valid_at, superseded_at, truth_status_code
    INTO scenario_target_valid_at, scenario_superseded_at,
         scenario_truth_status_code
    FROM architecture_core.architecture_scenario
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_scenario_id = NEW.architecture_scenario_id;

  IF scenario_target_valid_at IS NOT NULL THEN
    SELECT EXISTS (
      SELECT 1
        FROM architecture_core.scenario_baseline AS scenario_baseline
       WHERE scenario_baseline.tenant_record_id = NEW.tenant_record_id
         AND scenario_baseline.architecture_scenario_id =
             NEW.architecture_scenario_id
    ) INTO baseline_exists;

    IF NOT baseline_exists THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'scenario delta requires an immutable scenario baseline';
    END IF;

    IF NEW.effective_from > scenario_target_valid_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'scenario delta begins after the scenario target time';
    END IF;

    IF scenario_superseded_at IS NOT NULL
       OR scenario_truth_status_code IN ('superseded', 'rejected') THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'scenario delta cannot be appended to an inactive scenario';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

CREATE FUNCTION architecture_core.reject_scenario_meaning_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'versioned scenario meaning is immutable; append or supersede instead';
END;
$$;

CREATE FUNCTION architecture_core.reject_scenario_baseline_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'scenario baseline is immutable; create a new scenario instead';
END;
$$;

CREATE FUNCTION architecture_core.validate_scenario_supersession()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.superseded_at IS NOT NULL
     AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'scenario supersession time is immutable once recorded';
  END IF;

  RETURN NEW;
END;
$$;

CREATE FUNCTION architecture_core.reject_scenario_history_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'scenario history cannot be hard deleted; supersede instead';
END;
$$;

CREATE TRIGGER architecture_scenario_immutable_guard
BEFORE UPDATE OF
    tenant_record_id,
    architecture_scenario_id,
    scenario_code,
    scenario_title,
    scenario_description,
    target_valid_at,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.architecture_scenario
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_meaning_mutation();

CREATE TRIGGER architecture_scenario_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.architecture_scenario
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_scenario_supersession();

CREATE TRIGGER architecture_scenario_delete_guard
BEFORE DELETE ON architecture_core.architecture_scenario
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_history_delete();

CREATE TRIGGER scenario_baseline_semantic_guard
BEFORE INSERT ON architecture_core.scenario_baseline
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_scenario_baseline_semantics();

CREATE TRIGGER scenario_baseline_immutable_guard
BEFORE UPDATE ON architecture_core.scenario_baseline
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_baseline_mutation();

CREATE TRIGGER scenario_baseline_delete_guard
BEFORE DELETE ON architecture_core.scenario_baseline
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_history_delete();

CREATE TRIGGER scenario_object_delta_semantic_guard
BEFORE INSERT ON architecture_core.scenario_object_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_scenario_delta_semantics();

CREATE TRIGGER scenario_object_delta_immutable_guard
BEFORE UPDATE OF
    tenant_record_id,
    scenario_object_delta_id,
    architecture_scenario_id,
    sequence_number,
    architecture_object_id,
    desired_presence_code,
    effective_from,
    effective_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.scenario_object_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_meaning_mutation();

CREATE TRIGGER scenario_object_delta_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.scenario_object_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_scenario_supersession();

CREATE TRIGGER scenario_object_delta_delete_guard
BEFORE DELETE ON architecture_core.scenario_object_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_history_delete();

CREATE FUNCTION architecture_core.project_scenario_objects(
    requested_scenario_id uuid
)
RETURNS TABLE (
    architecture_object_id uuid,
    is_present boolean,
    projection_origin_code text,
    applied_sequence_number integer,
    projection_truth_status_code text
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  PERFORM 1
    FROM architecture_core.architecture_scenario AS architecture_scenario
    JOIN architecture_core.scenario_baseline AS scenario_baseline
      ON scenario_baseline.tenant_record_id =
         architecture_scenario.tenant_record_id
     AND scenario_baseline.architecture_scenario_id =
         architecture_scenario.architecture_scenario_id
   WHERE architecture_scenario.tenant_record_id =
         architecture_core.current_tenant_id()
     AND architecture_scenario.architecture_scenario_id =
         requested_scenario_id
     AND architecture_scenario.superseded_at IS NULL
     AND architecture_scenario.truth_status_code NOT IN
         ('superseded', 'rejected');

  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'active scenario with immutable baseline is unavailable';
  END IF;

  RETURN QUERY
  WITH scenario_context AS (
    SELECT
      architecture_scenario.tenant_record_id,
      architecture_scenario.target_valid_at,
      scenario_baseline.baseline_valid_at,
      scenario_baseline.baseline_recorded_at
    FROM architecture_core.architecture_scenario AS architecture_scenario
    JOIN architecture_core.scenario_baseline AS scenario_baseline
      ON scenario_baseline.tenant_record_id =
         architecture_scenario.tenant_record_id
     AND scenario_baseline.architecture_scenario_id =
         architecture_scenario.architecture_scenario_id
   WHERE architecture_scenario.tenant_record_id =
         architecture_core.current_tenant_id()
     AND architecture_scenario.architecture_scenario_id =
         requested_scenario_id
     AND architecture_scenario.superseded_at IS NULL
     AND architecture_scenario.truth_status_code NOT IN
         ('superseded', 'rejected')
  ),
  baseline_object AS (
    SELECT DISTINCT object_revision.architecture_object_id
      FROM architecture_core.object_revision AS object_revision
      CROSS JOIN scenario_context
     WHERE object_revision.tenant_record_id =
           scenario_context.tenant_record_id
       AND object_revision.truth_status_code = 'authoritative'
       AND object_revision.valid_from <= scenario_context.baseline_valid_at
       AND (
          object_revision.valid_to IS NULL
          OR object_revision.valid_to > scenario_context.baseline_valid_at
       )
       AND object_revision.recorded_at <=
           scenario_context.baseline_recorded_at
       AND (
          object_revision.superseded_at IS NULL
          OR object_revision.superseded_at >
             scenario_context.baseline_recorded_at
       )
  ),
  ranked_delta AS (
    SELECT
      scenario_object_delta.scenario_object_delta_id,
      scenario_object_delta.architecture_object_id,
      scenario_object_delta.desired_presence_code,
      scenario_object_delta.sequence_number,
      scenario_object_delta.truth_status_code,
      row_number() OVER (
        PARTITION BY scenario_object_delta.architecture_object_id
        ORDER BY scenario_object_delta.sequence_number DESC
      ) AS delta_rank
      FROM architecture_core.scenario_object_delta AS scenario_object_delta
      CROSS JOIN scenario_context
     WHERE scenario_object_delta.tenant_record_id =
           scenario_context.tenant_record_id
       AND scenario_object_delta.architecture_scenario_id =
           requested_scenario_id
       AND scenario_object_delta.superseded_at IS NULL
       AND scenario_object_delta.truth_status_code NOT IN
           ('superseded', 'rejected')
       AND scenario_object_delta.effective_from <=
           scenario_context.target_valid_at
       AND (
          scenario_object_delta.effective_to IS NULL
          OR scenario_object_delta.effective_to >
             scenario_context.target_valid_at
       )
  ),
  latest_delta AS (
    SELECT
      ranked_delta.scenario_object_delta_id,
      ranked_delta.architecture_object_id,
      ranked_delta.desired_presence_code,
      ranked_delta.sequence_number,
      ranked_delta.truth_status_code
      FROM ranked_delta
     WHERE ranked_delta.delta_rank = 1
  ),
  candidate_object AS (
    SELECT baseline_object.architecture_object_id
      FROM baseline_object
    UNION
    SELECT latest_delta.architecture_object_id
      FROM latest_delta
  )
  SELECT
    candidate_object.architecture_object_id,
    CASE
      WHEN latest_delta.scenario_object_delta_id IS NOT NULL
        THEN latest_delta.desired_presence_code = 'present'
      ELSE true
    END AS is_present,
    CASE
      WHEN latest_delta.scenario_object_delta_id IS NOT NULL
        THEN 'scenario_delta'
      ELSE 'baseline'
    END::text AS projection_origin_code,
    latest_delta.sequence_number AS applied_sequence_number,
    CASE
      WHEN latest_delta.scenario_object_delta_id IS NOT NULL
        THEN latest_delta.truth_status_code
      ELSE 'authoritative'
    END::text AS projection_truth_status_code
    FROM candidate_object
    LEFT JOIN latest_delta
      ON latest_delta.architecture_object_id =
         candidate_object.architecture_object_id
   ORDER BY candidate_object.architecture_object_id;
END;
$$;

CREATE INDEX scenario_object_delta_projection_index
    ON architecture_core.scenario_object_delta
        (
            tenant_record_id,
            architecture_scenario_id,
            architecture_object_id,
            sequence_number DESC
        )
    WHERE superseded_at IS NULL;

ALTER TABLE architecture_core.architecture_scenario ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.architecture_scenario FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.architecture_scenario
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.scenario_baseline ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.scenario_baseline FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.scenario_baseline
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.scenario_object_delta ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.scenario_object_delta FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.scenario_object_delta
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

COMMIT;