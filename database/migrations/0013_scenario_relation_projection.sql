BEGIN;

CREATE TABLE architecture_core.scenario_relation_delta (
    tenant_record_id uuid NOT NULL,
    scenario_relation_delta_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_scenario_id uuid NOT NULL,
    sequence_number integer NOT NULL,
    relation_type_id uuid NOT NULL,
    source_object_id uuid NOT NULL,
    target_object_id uuid NOT NULL,
    desired_presence_code text NOT NULL,
    effective_from timestamptz NOT NULL,
    effective_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT scenario_relation_delta_primary_key
        PRIMARY KEY (tenant_record_id, scenario_relation_delta_id),
    CONSTRAINT scenario_relation_delta_scenario_foreign
        FOREIGN KEY (tenant_record_id, architecture_scenario_id)
        REFERENCES architecture_core.architecture_scenario
            (tenant_record_id, architecture_scenario_id),
    CONSTRAINT scenario_relation_delta_type_foreign
        FOREIGN KEY (relation_type_id)
        REFERENCES architecture_core.relation_type (relation_type_id),
    CONSTRAINT scenario_relation_delta_source_foreign
        FOREIGN KEY (tenant_record_id, source_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT scenario_relation_delta_target_foreign
        FOREIGN KEY (tenant_record_id, target_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT scenario_relation_delta_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT scenario_relation_delta_uuid_version
        CHECK (uuid_extract_version(scenario_relation_delta_id) = 7),
    CONSTRAINT scenario_relation_delta_no_self
        CHECK (source_object_id <> target_object_id),
    CONSTRAINT scenario_relation_delta_sequence_positive
        CHECK (sequence_number > 0),
    CONSTRAINT scenario_relation_delta_presence_allowed
        CHECK (desired_presence_code IN ('present', 'absent')),
    CONSTRAINT scenario_relation_delta_effective_interval
        CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT scenario_relation_delta_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT scenario_relation_delta_truth_allowed
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
    CONSTRAINT scenario_relation_delta_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT scenario_relation_delta_sequence_unique
        UNIQUE (tenant_record_id, architecture_scenario_id, sequence_number)
);

ALTER TABLE architecture_core.scenario_relation_delta ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.scenario_relation_delta FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.scenario_relation_delta
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE FUNCTION architecture_core.validate_scenario_relation_delta_semantics()
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
        MESSAGE = 'scenario relation delta requires an immutable scenario baseline';
    END IF;

    IF NEW.effective_from > scenario_target_valid_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'scenario relation delta begins after the scenario target time';
    END IF;

    IF scenario_superseded_at IS NOT NULL
       OR scenario_truth_status_code IN ('superseded', 'rejected') THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'scenario relation delta cannot be appended to an inactive scenario';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER scenario_relation_delta_semantic_guard
BEFORE INSERT ON architecture_core.scenario_relation_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_scenario_relation_delta_semantics();

CREATE TRIGGER scenario_relation_delta_type_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    relation_type_id,
    source_object_id,
    target_object_id
ON architecture_core.scenario_relation_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_architecture_relation_types();

CREATE TRIGGER scenario_relation_delta_immutable_guard
BEFORE UPDATE OF
    tenant_record_id,
    scenario_relation_delta_id,
    architecture_scenario_id,
    sequence_number,
    relation_type_id,
    source_object_id,
    target_object_id,
    desired_presence_code,
    effective_from,
    effective_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.scenario_relation_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_meaning_mutation();

CREATE TRIGGER scenario_relation_delta_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.scenario_relation_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_scenario_supersession();

CREATE TRIGGER scenario_relation_delta_delete_guard
BEFORE DELETE ON architecture_core.scenario_relation_delta
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_scenario_history_delete();

CREATE FUNCTION architecture_core.project_scenario_relations(
    requested_scenario_id uuid
)
RETURNS TABLE (
    relation_type_id uuid,
    source_object_id uuid,
    target_object_id uuid,
    is_present boolean,
    desired_presence_code text,
    projection_origin_code text,
    applied_sequence_number integer,
    projection_truth_status_code text,
    baseline_architecture_relation_id uuid,
    scenario_relation_delta_id uuid,
    endpoint_integrity_code text
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
  baseline_relation AS (
    SELECT
      architecture_relation.architecture_relation_id,
      architecture_relation.relation_type_id,
      architecture_relation.source_object_id,
      architecture_relation.target_object_id
      FROM architecture_core.architecture_relation AS architecture_relation
      CROSS JOIN scenario_context
     WHERE architecture_relation.tenant_record_id =
           scenario_context.tenant_record_id
       AND architecture_relation.truth_status_code = 'authoritative'
       AND architecture_relation.valid_from <=
           scenario_context.baseline_valid_at
       AND (
          architecture_relation.valid_to IS NULL
          OR architecture_relation.valid_to > scenario_context.baseline_valid_at
       )
       AND architecture_relation.recorded_at <=
           scenario_context.baseline_recorded_at
       AND (
          architecture_relation.superseded_at IS NULL
          OR architecture_relation.superseded_at >
             scenario_context.baseline_recorded_at
       )
  ),
  ranked_delta AS (
    SELECT
      scenario_relation_delta.scenario_relation_delta_id,
      scenario_relation_delta.relation_type_id,
      scenario_relation_delta.source_object_id,
      scenario_relation_delta.target_object_id,
      scenario_relation_delta.desired_presence_code,
      scenario_relation_delta.sequence_number,
      scenario_relation_delta.truth_status_code,
      row_number() OVER (
        PARTITION BY
          scenario_relation_delta.relation_type_id,
          scenario_relation_delta.source_object_id,
          scenario_relation_delta.target_object_id
        ORDER BY scenario_relation_delta.sequence_number DESC
      ) AS delta_rank
      FROM architecture_core.scenario_relation_delta AS scenario_relation_delta
      CROSS JOIN scenario_context
     WHERE scenario_relation_delta.tenant_record_id =
           scenario_context.tenant_record_id
       AND scenario_relation_delta.architecture_scenario_id =
           requested_scenario_id
       AND scenario_relation_delta.superseded_at IS NULL
       AND scenario_relation_delta.truth_status_code NOT IN
           ('superseded', 'rejected')
       AND scenario_relation_delta.effective_from <=
           scenario_context.target_valid_at
       AND (
          scenario_relation_delta.effective_to IS NULL
          OR scenario_relation_delta.effective_to >
             scenario_context.target_valid_at
       )
  ),
  latest_delta AS (
    SELECT
      ranked_delta.scenario_relation_delta_id,
      ranked_delta.relation_type_id,
      ranked_delta.source_object_id,
      ranked_delta.target_object_id,
      ranked_delta.desired_presence_code,
      ranked_delta.sequence_number,
      ranked_delta.truth_status_code
      FROM ranked_delta
     WHERE ranked_delta.delta_rank = 1
  ),
  candidate_relation AS (
    SELECT
      baseline_relation.relation_type_id,
      baseline_relation.source_object_id,
      baseline_relation.target_object_id
      FROM baseline_relation
    UNION
    SELECT
      latest_delta.relation_type_id,
      latest_delta.source_object_id,
      latest_delta.target_object_id
      FROM latest_delta
  ),
  resolved_relation AS (
    SELECT
      candidate_relation.relation_type_id,
      candidate_relation.source_object_id,
      candidate_relation.target_object_id,
      baseline_relation.architecture_relation_id,
      latest_delta.scenario_relation_delta_id,
      COALESCE(latest_delta.desired_presence_code, 'present')
        AS desired_presence_code,
      latest_delta.sequence_number,
      COALESCE(latest_delta.truth_status_code, 'authoritative')
        AS truth_status_code,
      CASE
        WHEN latest_delta.scenario_relation_delta_id IS NOT NULL
          THEN 'scenario_delta'
        ELSE 'baseline'
      END::text AS origin_code
      FROM candidate_relation
      LEFT JOIN baseline_relation
        ON baseline_relation.relation_type_id = candidate_relation.relation_type_id
       AND baseline_relation.source_object_id = candidate_relation.source_object_id
       AND baseline_relation.target_object_id = candidate_relation.target_object_id
      LEFT JOIN latest_delta
        ON latest_delta.relation_type_id = candidate_relation.relation_type_id
       AND latest_delta.source_object_id = candidate_relation.source_object_id
       AND latest_delta.target_object_id = candidate_relation.target_object_id
  ),
  projected_object AS (
    SELECT
      projected.architecture_object_id,
      projected.is_present
      FROM architecture_core.project_scenario_objects(
          requested_scenario_id
      ) AS projected
  )
  SELECT
    resolved_relation.relation_type_id,
    resolved_relation.source_object_id,
    resolved_relation.target_object_id,
    (
      resolved_relation.desired_presence_code = 'present'
      AND COALESCE(source_projection.is_present, false)
      AND COALESCE(target_projection.is_present, false)
    ) AS is_present,
    resolved_relation.desired_presence_code,
    resolved_relation.origin_code AS projection_origin_code,
    resolved_relation.sequence_number AS applied_sequence_number,
    resolved_relation.truth_status_code AS projection_truth_status_code,
    resolved_relation.architecture_relation_id
      AS baseline_architecture_relation_id,
    resolved_relation.scenario_relation_delta_id,
    CASE
      WHEN COALESCE(source_projection.is_present, false)
       AND COALESCE(target_projection.is_present, false)
        THEN 'valid'
      WHEN NOT COALESCE(source_projection.is_present, false)
       AND NOT COALESCE(target_projection.is_present, false)
        THEN 'both_absent'
      WHEN NOT COALESCE(source_projection.is_present, false)
        THEN 'source_absent'
      ELSE 'target_absent'
    END::text AS endpoint_integrity_code
    FROM resolved_relation
    LEFT JOIN projected_object AS source_projection
      ON source_projection.architecture_object_id =
         resolved_relation.source_object_id
    LEFT JOIN projected_object AS target_projection
      ON target_projection.architecture_object_id =
         resolved_relation.target_object_id
   ORDER BY
     resolved_relation.relation_type_id,
     resolved_relation.source_object_id,
     resolved_relation.target_object_id;
END;
$$;

COMMIT;
