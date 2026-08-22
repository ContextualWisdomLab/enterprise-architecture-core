BEGIN;

CREATE FUNCTION architecture_core.read_portfolio_assessment_for_tenant(
    requested_tenant_record_id uuid,
    requested_architecture_object_id uuid,
    assessment_valid_at timestamptz,
    assessment_recorded_at timestamptz,
    requested_framework_code text DEFAULT NULL,
    requested_cycle_code text DEFAULT NULL
)
RETURNS TABLE (
    architecture_object_id uuid,
    assessment_framework_code text,
    assessment_framework_title text,
    assessment_framework_version_label text,
    assessment_scale_code text,
    assessment_dimension_code text,
    assessment_dimension_title text,
    assessment_cycle_code text,
    assessment_cycle_title text,
    score_value numeric,
    score_label text,
    truth_status_code text,
    evidence_record_id uuid,
    valid_from timestamptz,
    valid_to timestamptz,
    recorded_at timestamptz
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  previous_tenant_setting text;
BEGIN
  IF requested_tenant_record_id IS NULL
     OR requested_architecture_object_id IS NULL
     OR assessment_valid_at IS NULL
     OR assessment_recorded_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant, architecture object, and assessment cutoffs are required';
  END IF;

  IF uuid_extract_version(requested_architecture_object_id) IS DISTINCT FROM 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'architecture object id must be canonical UUIDv7';
  END IF;

  IF requested_framework_code IS NOT NULL
     AND requested_framework_code !~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'framework code must be lower snake case';
  END IF;

  IF requested_cycle_code IS NOT NULL
     AND requested_cycle_code !~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'cycle code must be lower snake case';
  END IF;

  previous_tenant_setting := pg_catalog.current_setting(
      'app.tenant_record_id',
      true
  );
  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  BEGIN
    RETURN QUERY
    SELECT
      assessment.architecture_object_id,
      framework.framework_code,
      framework.framework_title,
      framework.framework_version_label,
      assessment_scale.scale_code,
      dimension.dimension_code,
      dimension.dimension_title,
      cycle.cycle_code,
      cycle.cycle_title,
      scale_value.score_value,
      scale_value.score_label,
      assessment.truth_status_code,
      assessment.evidence_record_id,
      assessment.valid_from,
      assessment.valid_to,
      assessment.recorded_at
    FROM architecture_core.architecture_object AS object_record
    JOIN architecture_core.object_type AS object_type
      ON object_type.object_type_id = object_record.object_type_id
    JOIN LATERAL (
      SELECT object_revision.*
        FROM architecture_core.object_revision AS object_revision
       WHERE object_revision.tenant_record_id = requested_tenant_record_id
         AND object_revision.architecture_object_id =
             object_record.architecture_object_id
         AND object_revision.valid_from <= assessment_valid_at
         AND (
           object_revision.valid_to IS NULL
           OR assessment_valid_at < object_revision.valid_to
         )
         AND object_revision.recorded_at <= assessment_recorded_at
         AND (
           object_revision.superseded_at IS NULL
           OR assessment_recorded_at < object_revision.superseded_at
         )
         AND object_revision.truth_status_code NOT IN ('superseded', 'rejected')
       ORDER BY
         object_revision.valid_from DESC,
         object_revision.recorded_at DESC,
         object_revision.revision_number DESC
       LIMIT 1
    ) AS selected_revision ON true
    JOIN architecture_core.object_assessment AS assessment
      ON assessment.tenant_record_id = requested_tenant_record_id
     AND assessment.architecture_object_id = object_record.architecture_object_id
    JOIN architecture_core.assessment_dimension AS dimension
      ON dimension.tenant_record_id = requested_tenant_record_id
     AND dimension.assessment_dimension_id = assessment.assessment_dimension_id
    JOIN architecture_core.assessment_scale AS assessment_scale
      ON assessment_scale.tenant_record_id = requested_tenant_record_id
     AND assessment_scale.assessment_scale_id = dimension.assessment_scale_id
    JOIN architecture_core.assessment_framework AS framework
      ON framework.tenant_record_id = requested_tenant_record_id
     AND framework.assessment_framework_id = assessment_scale.assessment_framework_id
    JOIN architecture_core.assessment_cycle AS cycle
      ON cycle.tenant_record_id = requested_tenant_record_id
     AND cycle.assessment_cycle_id = assessment.assessment_cycle_id
     AND cycle.assessment_framework_id = framework.assessment_framework_id
    JOIN architecture_core.assessment_scale_value AS scale_value
      ON scale_value.tenant_record_id = requested_tenant_record_id
     AND scale_value.scale_value_id = assessment.scale_value_id
    WHERE object_record.tenant_record_id = requested_tenant_record_id
      AND object_record.architecture_object_id = requested_architecture_object_id
      AND assessment.valid_from <= assessment_valid_at
      AND (
        assessment.valid_to IS NULL
        OR assessment_valid_at < assessment.valid_to
      )
      AND assessment.recorded_at <= assessment_recorded_at
      AND (
        assessment.superseded_at IS NULL
        OR assessment_recorded_at < assessment.superseded_at
      )
      AND assessment.truth_status_code NOT IN ('superseded', 'rejected')
      AND framework.valid_from <= assessment_valid_at
      AND (
        framework.valid_to IS NULL
        OR assessment_valid_at < framework.valid_to
      )
      AND framework.recorded_at <= assessment_recorded_at
      AND (
        framework.superseded_at IS NULL
        OR assessment_recorded_at < framework.superseded_at
      )
      AND cycle.valid_from <= assessment_valid_at
      AND assessment_valid_at < cycle.valid_to
      AND cycle.recorded_at <= assessment_recorded_at
      AND (
        cycle.superseded_at IS NULL
        OR assessment_recorded_at < cycle.superseded_at
      )
      AND assessment_scale.recorded_at <= assessment_recorded_at
      AND scale_value.recorded_at <= assessment_recorded_at
      AND dimension.recorded_at <= assessment_recorded_at
      AND (
        requested_framework_code IS NULL
        OR framework.framework_code = requested_framework_code
      )
      AND (
        requested_cycle_code IS NULL
        OR cycle.cycle_code = requested_cycle_code
      )
    ORDER BY
      framework.framework_code,
      cycle.cycle_code,
      dimension.dimension_code,
      assessment.valid_from,
      assessment.recorded_at;
  EXCEPTION WHEN OTHERS THEN
    PERFORM pg_catalog.set_config(
        'app.tenant_record_id',
        COALESCE(previous_tenant_setting, ''),
        true
    );
    RAISE;
  END;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      COALESCE(previous_tenant_setting, ''),
      true
  );
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.read_portfolio_assessment_for_tenant(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    text,
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
      'GRANT EXECUTE ON FUNCTION '
      'architecture_core.read_portfolio_assessment_for_tenant('
      'uuid,uuid,timestamptz,timestamptz,text,text) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.read_portfolio_assessment_for_tenant(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    text,
    text
) IS
'Purpose-bound tenant-scoped bitemporal portfolio assessment read port. The service verifies Keyverse identity and passes only the verified tenant and canonical query cutoffs; the runtime role receives no direct assessment-table authority, and superseded or rejected facts never appear as buyer assessment evidence.';

COMMIT;
