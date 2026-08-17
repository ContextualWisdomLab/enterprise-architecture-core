BEGIN;

CREATE TABLE architecture_core.assessment_framework (
    tenant_record_id uuid NOT NULL,
    assessment_framework_id uuid NOT NULL DEFAULT uuidv7(),
    framework_code text NOT NULL,
    framework_title text NOT NULL,
    framework_version_label text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    CONSTRAINT assessment_framework_primary_key
        PRIMARY KEY (tenant_record_id, assessment_framework_id),
    CONSTRAINT assessment_framework_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT assessment_framework_uuid_version
        CHECK (uuid_extract_version(assessment_framework_id) = 7),
    CONSTRAINT assessment_framework_code_format
        CHECK (framework_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT assessment_framework_title_nonempty
        CHECK (length(btrim(framework_title)) > 0),
    CONSTRAINT assessment_framework_version_nonempty
        CHECK (length(btrim(framework_version_label)) > 0),
    CONSTRAINT assessment_framework_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT assessment_framework_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT assessment_framework_version_unique
        UNIQUE (tenant_record_id, framework_code, framework_version_label),
    CONSTRAINT assessment_framework_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            framework_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (superseded_at IS NULL)
);

CREATE TABLE architecture_core.assessment_scale (
    tenant_record_id uuid NOT NULL,
    assessment_scale_id uuid NOT NULL DEFAULT uuidv7(),
    assessment_framework_id uuid NOT NULL,
    scale_code text NOT NULL,
    scale_title text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_scale_primary_key
        PRIMARY KEY (tenant_record_id, assessment_scale_id),
    CONSTRAINT assessment_scale_framework_foreign
        FOREIGN KEY (tenant_record_id, assessment_framework_id)
        REFERENCES architecture_core.assessment_framework
            (tenant_record_id, assessment_framework_id),
    CONSTRAINT assessment_scale_uuid_version
        CHECK (uuid_extract_version(assessment_scale_id) = 7),
    CONSTRAINT assessment_scale_code_format
        CHECK (scale_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT assessment_scale_title_nonempty
        CHECK (length(btrim(scale_title)) > 0),
    CONSTRAINT assessment_scale_code_unique
        UNIQUE (tenant_record_id, assessment_framework_id, scale_code)
);

CREATE TABLE architecture_core.assessment_scale_value (
    tenant_record_id uuid NOT NULL,
    scale_value_id uuid NOT NULL DEFAULT uuidv7(),
    assessment_scale_id uuid NOT NULL,
    score_value numeric(12, 4) NOT NULL,
    score_label text NOT NULL,
    ordinal_rank integer NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_scale_value_primary_key
        PRIMARY KEY (tenant_record_id, scale_value_id),
    CONSTRAINT assessment_scale_value_scale_foreign
        FOREIGN KEY (tenant_record_id, assessment_scale_id)
        REFERENCES architecture_core.assessment_scale
            (tenant_record_id, assessment_scale_id),
    CONSTRAINT assessment_scale_value_uuid_version
        CHECK (uuid_extract_version(scale_value_id) = 7),
    CONSTRAINT assessment_scale_value_label_nonempty
        CHECK (length(btrim(score_label)) > 0),
    CONSTRAINT assessment_scale_value_rank_positive
        CHECK (ordinal_rank > 0),
    CONSTRAINT assessment_scale_value_score_unique
        UNIQUE (tenant_record_id, assessment_scale_id, score_value),
    CONSTRAINT assessment_scale_value_rank_unique
        UNIQUE (tenant_record_id, assessment_scale_id, ordinal_rank)
);

CREATE TABLE architecture_core.assessment_dimension (
    tenant_record_id uuid NOT NULL,
    assessment_dimension_id uuid NOT NULL DEFAULT uuidv7(),
    assessment_scale_id uuid NOT NULL,
    dimension_code text NOT NULL,
    dimension_title text NOT NULL,
    dimension_description text,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_dimension_primary_key
        PRIMARY KEY (tenant_record_id, assessment_dimension_id),
    CONSTRAINT assessment_dimension_scale_foreign
        FOREIGN KEY (tenant_record_id, assessment_scale_id)
        REFERENCES architecture_core.assessment_scale
            (tenant_record_id, assessment_scale_id),
    CONSTRAINT assessment_dimension_uuid_version
        CHECK (uuid_extract_version(assessment_dimension_id) = 7),
    CONSTRAINT assessment_dimension_code_format
        CHECK (dimension_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT assessment_dimension_title_nonempty
        CHECK (length(btrim(dimension_title)) > 0),
    CONSTRAINT assessment_dimension_description_length
        CHECK (
            dimension_description IS NULL
            OR length(dimension_description) BETWEEN 1 AND 4096
        ),
    CONSTRAINT assessment_dimension_code_unique
        UNIQUE (tenant_record_id, assessment_scale_id, dimension_code)
);

CREATE TABLE architecture_core.assessment_cycle (
    tenant_record_id uuid NOT NULL,
    assessment_cycle_id uuid NOT NULL DEFAULT uuidv7(),
    assessment_framework_id uuid NOT NULL,
    cycle_code text NOT NULL,
    cycle_title text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    CONSTRAINT assessment_cycle_primary_key
        PRIMARY KEY (tenant_record_id, assessment_cycle_id),
    CONSTRAINT assessment_cycle_framework_foreign
        FOREIGN KEY (tenant_record_id, assessment_framework_id)
        REFERENCES architecture_core.assessment_framework
            (tenant_record_id, assessment_framework_id),
    CONSTRAINT assessment_cycle_uuid_version
        CHECK (uuid_extract_version(assessment_cycle_id) = 7),
    CONSTRAINT assessment_cycle_code_format
        CHECK (cycle_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT assessment_cycle_title_nonempty
        CHECK (length(btrim(cycle_title)) > 0),
    CONSTRAINT assessment_cycle_valid_interval
        CHECK (valid_to > valid_from),
    CONSTRAINT assessment_cycle_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT assessment_cycle_code_unique
        UNIQUE (tenant_record_id, assessment_framework_id, cycle_code)
);

CREATE TABLE architecture_core.object_assessment (
    tenant_record_id uuid NOT NULL,
    object_assessment_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_object_id uuid NOT NULL,
    assessment_dimension_id uuid NOT NULL,
    assessment_cycle_id uuid NOT NULL,
    scale_value_id uuid NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    assessor_note text,
    CONSTRAINT object_assessment_primary_key
        PRIMARY KEY (tenant_record_id, object_assessment_id),
    CONSTRAINT object_assessment_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT object_assessment_dimension_foreign
        FOREIGN KEY (tenant_record_id, assessment_dimension_id)
        REFERENCES architecture_core.assessment_dimension
            (tenant_record_id, assessment_dimension_id),
    CONSTRAINT object_assessment_cycle_foreign
        FOREIGN KEY (tenant_record_id, assessment_cycle_id)
        REFERENCES architecture_core.assessment_cycle
            (tenant_record_id, assessment_cycle_id),
    CONSTRAINT object_assessment_scale_value_foreign
        FOREIGN KEY (tenant_record_id, scale_value_id)
        REFERENCES architecture_core.assessment_scale_value
            (tenant_record_id, scale_value_id),
    CONSTRAINT object_assessment_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT object_assessment_uuid_version
        CHECK (uuid_extract_version(object_assessment_id) = 7),
    CONSTRAINT object_assessment_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT object_assessment_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT object_assessment_truth_allowed
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
    CONSTRAINT object_assessment_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT object_assessment_note_length
        CHECK (
            assessor_note IS NULL
            OR length(assessor_note) BETWEEN 1 AND 4096
        ),
    CONSTRAINT object_assessment_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            architecture_object_id WITH =,
            assessment_dimension_id WITH =,
            assessment_cycle_id WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE FUNCTION architecture_core.validate_object_assessment_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  dimension_scale_id uuid;
  dimension_framework_id uuid;
  cycle_framework_id uuid;
  value_scale_id uuid;
BEGIN
  SELECT
      assessment_dimension.assessment_scale_id,
      assessment_scale.assessment_framework_id
    INTO dimension_scale_id, dimension_framework_id
    FROM architecture_core.assessment_dimension AS assessment_dimension
    JOIN architecture_core.assessment_scale AS assessment_scale
      ON assessment_scale.tenant_record_id = assessment_dimension.tenant_record_id
     AND assessment_scale.assessment_scale_id = assessment_dimension.assessment_scale_id
   WHERE assessment_dimension.tenant_record_id = NEW.tenant_record_id
     AND assessment_dimension.assessment_dimension_id = NEW.assessment_dimension_id;

  SELECT assessment_cycle.assessment_framework_id
    INTO cycle_framework_id
    FROM architecture_core.assessment_cycle AS assessment_cycle
   WHERE assessment_cycle.tenant_record_id = NEW.tenant_record_id
     AND assessment_cycle.assessment_cycle_id = NEW.assessment_cycle_id;

  SELECT assessment_scale_value.assessment_scale_id
    INTO value_scale_id
    FROM architecture_core.assessment_scale_value AS assessment_scale_value
   WHERE assessment_scale_value.tenant_record_id = NEW.tenant_record_id
     AND assessment_scale_value.scale_value_id = NEW.scale_value_id;

  IF dimension_scale_id IS NOT NULL
     AND value_scale_id IS DISTINCT FROM dimension_scale_id THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment scale value does not belong to the dimension scale';
  END IF;

  IF dimension_framework_id IS NOT NULL
     AND cycle_framework_id IS DISTINCT FROM dimension_framework_id THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment cycle does not belong to the dimension framework';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER object_assessment_semantic_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    assessment_dimension_id,
    assessment_cycle_id,
    scale_value_id
ON architecture_core.object_assessment
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_object_assessment_semantics();

ALTER TABLE architecture_core.assessment_framework ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_framework FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.assessment_framework
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_scale ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_scale FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.assessment_scale
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_scale_value ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_scale_value FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.assessment_scale_value
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_dimension ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_dimension FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.assessment_dimension
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_cycle ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_cycle FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.assessment_cycle
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.object_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.object_assessment FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.object_assessment
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

COMMIT;
