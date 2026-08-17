BEGIN;

CREATE FUNCTION architecture_core.project_technology_change_impact(
    requested_technology_version_id uuid,
    assessment_valid_at timestamptz,
    assessment_recorded_at timestamptz,
    planning_horizon_days integer DEFAULT 180
)
RETURNS TABLE (
    technology_version_id uuid,
    technology_component_id uuid,
    application_object_id uuid,
    capability_object_id uuid,
    component_code text,
    version_label text,
    application_code text,
    capability_code text,
    support_end_date date,
    lifecycle_phase_code text,
    impact_status_code text,
    evidence_state_code text,
    recommended_action_code text,
    version_relation_truth_status_code text,
    usage_relation_truth_status_code text,
    capability_relation_truth_status_code text,
    version_relation_evidence_record_id uuid,
    usage_relation_evidence_record_id uuid,
    capability_relation_evidence_record_id uuid,
    lifecycle_evidence_record_id uuid
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF planning_horizon_days < 1 OR planning_horizon_days > 3650 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'planning horizon must be between 1 and 3650 days';
  END IF;

  PERFORM 1
    FROM architecture_core.technology_version AS technology_version
   WHERE technology_version.tenant_record_id =
         architecture_core.current_tenant_id()
     AND technology_version.architecture_object_id =
         requested_technology_version_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'technology version is unavailable for the active tenant';
  END IF;

  RETURN QUERY
  WITH active_relation AS (
    SELECT
      architecture_relation.architecture_relation_id,
      architecture_relation.source_object_id,
      architecture_relation.target_object_id,
      architecture_relation.truth_status_code,
      architecture_relation.evidence_record_id,
      relation_type.relation_type_code
      FROM architecture_core.architecture_relation AS architecture_relation
      JOIN architecture_core.relation_type AS relation_type
        ON relation_type.relation_type_id =
           architecture_relation.relation_type_id
     WHERE architecture_relation.tenant_record_id =
           architecture_core.current_tenant_id()
       AND architecture_relation.valid_from <= assessment_valid_at
       AND (
          architecture_relation.valid_to IS NULL
          OR architecture_relation.valid_to > assessment_valid_at
       )
       AND architecture_relation.recorded_at <= assessment_recorded_at
       AND (
          architecture_relation.superseded_at IS NULL
          OR architecture_relation.superseded_at > assessment_recorded_at
       )
       AND architecture_relation.truth_status_code NOT IN
           ('superseded', 'rejected')
  ),
  version_path AS (
    SELECT
      has_version_relation.source_object_id AS technology_component_id,
      technology_component.component_code,
      has_version_relation.truth_status_code AS version_truth_status_code,
      has_version_relation.evidence_record_id AS version_evidence_record_id
      FROM active_relation AS has_version_relation
      JOIN architecture_core.technology_component AS technology_component
        ON technology_component.tenant_record_id =
           architecture_core.current_tenant_id()
       AND technology_component.architecture_object_id =
           has_version_relation.source_object_id
     WHERE has_version_relation.relation_type_code = 'has_version'
       AND has_version_relation.target_object_id =
           requested_technology_version_id
  ),
  application_path AS (
    SELECT
      version_path.technology_component_id,
      version_path.component_code,
      version_path.version_truth_status_code,
      version_path.version_evidence_record_id,
      uses_technology_relation.source_object_id AS application_object_id,
      application_record.application_code,
      uses_technology_relation.truth_status_code AS usage_truth_status_code,
      uses_technology_relation.evidence_record_id AS usage_evidence_record_id
      FROM version_path
      JOIN active_relation AS uses_technology_relation
        ON uses_technology_relation.relation_type_code = 'uses_technology'
       AND uses_technology_relation.target_object_id =
           version_path.technology_component_id
      JOIN architecture_core.application_record AS application_record
        ON application_record.tenant_record_id =
           architecture_core.current_tenant_id()
       AND application_record.architecture_object_id =
           uses_technology_relation.source_object_id
  ),
  impact_path AS (
    SELECT
      application_path.technology_component_id,
      application_path.component_code,
      application_path.version_truth_status_code,
      application_path.version_evidence_record_id,
      application_path.application_object_id,
      application_path.application_code,
      application_path.usage_truth_status_code,
      application_path.usage_evidence_record_id,
      supports_capability_relation.target_object_id AS capability_object_id,
      business_capability.capability_code,
      supports_capability_relation.truth_status_code AS capability_truth_status_code,
      supports_capability_relation.evidence_record_id AS capability_evidence_record_id
      FROM application_path
      LEFT JOIN active_relation AS supports_capability_relation
        ON supports_capability_relation.relation_type_code =
           'supports_capability'
       AND supports_capability_relation.source_object_id =
           application_path.application_object_id
      LEFT JOIN architecture_core.business_capability AS business_capability
        ON business_capability.tenant_record_id =
           architecture_core.current_tenant_id()
       AND business_capability.architecture_object_id =
           supports_capability_relation.target_object_id
  ),
  lifecycle_context AS (
    SELECT
      lifecycle_phase.lifecycle_phase_code,
      lifecycle_interval.evidence_record_id
      FROM architecture_core.lifecycle_interval AS lifecycle_interval
      JOIN architecture_core.lifecycle_phase AS lifecycle_phase
        ON lifecycle_phase.lifecycle_phase_id =
           lifecycle_interval.lifecycle_phase_id
     WHERE lifecycle_interval.tenant_record_id =
           architecture_core.current_tenant_id()
       AND lifecycle_interval.architecture_object_id =
           requested_technology_version_id
       AND lifecycle_interval.valid_from <= assessment_valid_at
       AND (
          lifecycle_interval.valid_to IS NULL
          OR lifecycle_interval.valid_to > assessment_valid_at
       )
       AND lifecycle_interval.recorded_at <= assessment_recorded_at
       AND (
          lifecycle_interval.superseded_at IS NULL
          OR lifecycle_interval.superseded_at > assessment_recorded_at
       )
     ORDER BY
       lifecycle_interval.recorded_at DESC,
       lifecycle_interval.valid_from DESC,
       lifecycle_interval.lifecycle_interval_id DESC
     LIMIT 1
  ),
  classified_impact AS (
    SELECT
      impact_path.*,
      technology_version.version_label,
      technology_version.support_end_date,
      lifecycle_context.lifecycle_phase_code,
      lifecycle_context.evidence_record_id AS lifecycle_evidence_record_id,
      CASE
        WHEN lifecycle_context.lifecycle_phase_code IN
             ('end_of_life', 'retired') THEN 'end_of_life'
        WHEN technology_version.support_end_date IS NOT NULL
         AND technology_version.support_end_date < assessment_valid_at::date
          THEN 'unsupported'
        WHEN lifecycle_context.lifecycle_phase_code = 'phase_out'
          THEN 'phase_out'
        WHEN technology_version.support_end_date IS NOT NULL
         AND technology_version.support_end_date <=
             assessment_valid_at::date + planning_horizon_days
          THEN 'support_ending_soon'
        ELSE 'supported'
      END::text AS impact_status_code,
      CASE
        WHEN impact_path.capability_object_id IS NULL
          THEN 'missing_capability_mapping'
        WHEN lifecycle_context.lifecycle_phase_code IS NULL
         AND technology_version.support_end_date IS NULL
          THEN 'missing_support_evidence'
        ELSE 'complete'
      END::text AS evidence_state_code
      FROM impact_path
      CROSS JOIN architecture_core.technology_version AS technology_version
      LEFT JOIN lifecycle_context ON true
     WHERE technology_version.tenant_record_id =
           architecture_core.current_tenant_id()
       AND technology_version.architecture_object_id =
           requested_technology_version_id
  )
  SELECT
    requested_technology_version_id AS technology_version_id,
    classified_impact.technology_component_id,
    classified_impact.application_object_id,
    classified_impact.capability_object_id,
    classified_impact.component_code,
    classified_impact.version_label,
    classified_impact.application_code,
    classified_impact.capability_code,
    classified_impact.support_end_date,
    classified_impact.lifecycle_phase_code,
    classified_impact.impact_status_code,
    classified_impact.evidence_state_code,
    CASE
      WHEN classified_impact.evidence_state_code =
           'missing_capability_mapping'
        THEN 'complete_capability_mapping'
      WHEN classified_impact.evidence_state_code = 'missing_support_evidence'
        THEN 'complete_support_evidence'
      WHEN classified_impact.impact_status_code IN
           ('end_of_life', 'unsupported')
        THEN 'start_remediation'
      WHEN classified_impact.impact_status_code IN
           ('phase_out', 'support_ending_soon')
        THEN 'plan_target_state'
      ELSE 'monitor'
    END::text AS recommended_action_code,
    classified_impact.version_truth_status_code,
    classified_impact.usage_truth_status_code,
    classified_impact.capability_truth_status_code,
    classified_impact.version_evidence_record_id,
    classified_impact.usage_evidence_record_id,
    classified_impact.capability_evidence_record_id,
    classified_impact.lifecycle_evidence_record_id
    FROM classified_impact
   ORDER BY
     classified_impact.application_object_id,
     classified_impact.capability_object_id NULLS FIRST,
     classified_impact.technology_component_id;
END;
$$;

COMMENT ON FUNCTION architecture_core.project_technology_change_impact(
    uuid,
    timestamptz,
    timestamptz,
    integer
) IS
'Projects a tenant-scoped, bitemporal technology-version impact path through EA-owned component, application, and capability relations. It preserves relation truth/evidence, surfaces missing mapping/support evidence, and returns deterministic next-action codes without mutating authoritative facts.';

COMMIT;
