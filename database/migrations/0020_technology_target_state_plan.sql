BEGIN;

CREATE FUNCTION architecture_core.project_technology_target_state_plan(
    requested_technology_version_id uuid,
    assessment_valid_at timestamptz,
    assessment_recorded_at timestamptz,
    planning_horizon_days integer DEFAULT 180
)
RETURNS TABLE (
    technology_version_id uuid,
    application_object_id uuid,
    capability_object_id uuid,
    application_code text,
    capability_code text,
    impact_status_code text,
    impact_evidence_state_code text,
    external_context_reference_id uuid,
    external_object_kind_code text,
    external_truth_status_code text,
    external_evidence_state_code text,
    remediation_initiative_id uuid,
    remediation_initiative_code text,
    architecture_scenario_id uuid,
    scenario_code text,
    architecture_transformation_id uuid,
    transformation_state_code text,
    decision_readiness_code text,
    recommended_action_code text
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF requested_technology_version_id IS NULL
     OR assessment_valid_at IS NULL
     OR assessment_recorded_at IS NULL
     OR planning_horizon_days IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE =
        'technology version, valid/system cutoffs, and planning horizon are required';
  END IF;

  IF planning_horizon_days < 1 OR planning_horizon_days > 3650 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'planning horizon must be between 1 and 3650 days';
  END IF;

  RETURN QUERY
  WITH technology_impact AS (
    SELECT *
      FROM architecture_core.project_technology_change_impact(
          requested_technology_version_id,
          assessment_valid_at,
          assessment_recorded_at,
          planning_horizon_days
      )
  ),
  active_transformation AS (
    SELECT
      architecture_transformation.architecture_transformation_id,
      architecture_transformation.architecture_scenario_id,
      architecture_transformation.remediation_initiative_id,
      remediation_initiative.initiative_code,
      architecture_scenario.scenario_code
      FROM architecture_core.architecture_transformation
      JOIN architecture_core.remediation_initiative
        ON remediation_initiative.tenant_record_id =
           architecture_transformation.tenant_record_id
       AND remediation_initiative.remediation_initiative_id =
           architecture_transformation.remediation_initiative_id
      JOIN architecture_core.architecture_scenario
        ON architecture_scenario.tenant_record_id =
           architecture_transformation.tenant_record_id
       AND architecture_scenario.architecture_scenario_id =
           architecture_transformation.architecture_scenario_id
     WHERE architecture_transformation.tenant_record_id =
           architecture_core.current_tenant_id()
       AND architecture_transformation.valid_from <= assessment_valid_at
       AND (
          architecture_transformation.valid_to IS NULL
          OR architecture_transformation.valid_to > assessment_valid_at
       )
       AND architecture_transformation.recorded_at <= assessment_recorded_at
       AND (
          architecture_transformation.superseded_at IS NULL
          OR architecture_transformation.superseded_at > assessment_recorded_at
       )
       AND architecture_transformation.truth_status_code NOT IN
           ('superseded', 'rejected')
       AND remediation_initiative.valid_from <= assessment_valid_at
       AND (
          remediation_initiative.valid_to IS NULL
          OR remediation_initiative.valid_to > assessment_valid_at
       )
       AND remediation_initiative.recorded_at <= assessment_recorded_at
       AND (
          remediation_initiative.superseded_at IS NULL
          OR remediation_initiative.superseded_at > assessment_recorded_at
       )
       AND remediation_initiative.truth_status_code NOT IN
           ('superseded', 'rejected')
       AND architecture_scenario.valid_from <= assessment_valid_at
       AND (
          architecture_scenario.valid_to IS NULL
          OR architecture_scenario.valid_to > assessment_valid_at
       )
       AND architecture_scenario.recorded_at <= assessment_recorded_at
       AND (
          architecture_scenario.superseded_at IS NULL
          OR architecture_scenario.superseded_at > assessment_recorded_at
       )
       AND architecture_scenario.truth_status_code NOT IN
           ('superseded', 'rejected')
  )
  SELECT
    technology_impact.technology_version_id,
    technology_impact.application_object_id,
    technology_impact.capability_object_id,
    technology_impact.application_code,
    technology_impact.capability_code,
    technology_impact.impact_status_code,
    technology_impact.evidence_state_code AS impact_evidence_state_code,
    external_impact.external_context_reference_id,
    external_impact.external_object_kind_code,
    external_impact.truth_status_code AS external_truth_status_code,
    external_impact.evidence_state_code AS external_evidence_state_code,
    transformation_match.remediation_initiative_id,
    transformation_match.initiative_code AS remediation_initiative_code,
    transformation_match.architecture_scenario_id,
    transformation_match.scenario_code,
    transformation_match.architecture_transformation_id,
    transformation_match.transformation_state_code,
    CASE
      WHEN technology_impact.evidence_state_code <> 'complete'
        THEN 'impact_evidence_incomplete'
      WHEN external_impact.external_context_reference_id IS NULL
        THEN 'cross_domain_evidence_missing'
      WHEN external_impact.evidence_state_code <> 'complete'
        THEN 'truth_review_required'
      WHEN transformation_match.architecture_transformation_id IS NULL
        THEN 'remediation_unplanned'
      WHEN transformation_match.transformation_state_code IS NULL
        THEN 'transformation_state_missing'
      WHEN transformation_match.transformation_state_code = 'proposed'
        THEN 'target_state_pending_approval'
      WHEN transformation_match.transformation_state_code = 'approved'
        THEN 'approved_not_started'
      WHEN transformation_match.transformation_state_code = 'started'
        THEN 'execution_in_progress'
      WHEN transformation_match.transformation_state_code = 'completed'
        THEN 'completed'
      WHEN transformation_match.transformation_state_code IN
           ('cancelled', 'rejected')
        THEN 'plan_blocked'
      ELSE 'transformation_state_unknown'
    END::text AS decision_readiness_code,
    CASE
      WHEN technology_impact.evidence_state_code <> 'complete'
        THEN technology_impact.recommended_action_code
      WHEN external_impact.external_context_reference_id IS NULL
        THEN 'collect_cross_domain_evidence'
      WHEN external_impact.evidence_state_code <> 'complete'
        THEN 'review_truth_origin'
      WHEN transformation_match.architecture_transformation_id IS NULL
        THEN 'create_remediation_initiative'
      WHEN transformation_match.transformation_state_code IS NULL
        THEN 'record_transformation_proposal'
      WHEN transformation_match.transformation_state_code = 'proposed'
        THEN 'approve_target_state'
      WHEN transformation_match.transformation_state_code = 'approved'
        THEN 'schedule_transformation'
      WHEN transformation_match.transformation_state_code = 'started'
        THEN 'monitor_transformation'
      WHEN transformation_match.transformation_state_code = 'completed'
        THEN 'verify_target_state'
      WHEN transformation_match.transformation_state_code IN
           ('cancelled', 'rejected')
        THEN 'replan_target_state'
      ELSE 'review_transformation_state'
    END::text AS recommended_action_code
    FROM technology_impact
    LEFT JOIN LATERAL architecture_core.project_application_context_impact(
        technology_impact.application_object_id,
        assessment_valid_at,
        assessment_recorded_at
    ) AS external_impact ON true
    LEFT JOIN LATERAL (
      SELECT
        active_transformation.architecture_transformation_id,
        active_transformation.architecture_scenario_id,
        active_transformation.remediation_initiative_id,
        active_transformation.initiative_code,
        active_transformation.scenario_code,
        transformation_state.transformation_state_code
        FROM active_transformation
        JOIN LATERAL architecture_core.project_scenario_objects_at(
            active_transformation.architecture_scenario_id,
            assessment_recorded_at
        ) AS scenario_object
          ON scenario_object.architecture_object_id =
             technology_impact.application_object_id
         AND scenario_object.is_present
        LEFT JOIN LATERAL (
          SELECT projected_state.transformation_state_code
            FROM architecture_core.project_transformation_state(
                active_transformation.architecture_transformation_id,
                assessment_valid_at,
                assessment_recorded_at
            ) AS projected_state
        ) AS transformation_state ON true
       ORDER BY
         active_transformation.architecture_transformation_id
       LIMIT 1
    ) AS transformation_match ON true
   ORDER BY
     technology_impact.application_object_id,
     technology_impact.capability_object_id NULLS FIRST,
     external_impact.external_object_kind_code NULLS FIRST,
     external_impact.external_context_reference_id NULLS FIRST;
END;
$$;

COMMENT ON FUNCTION architecture_core.project_technology_target_state_plan(
    uuid,
    timestamptz,
    timestamptz,
    integer
) IS
'Projects one tenant-scoped buyer decision surface from bitemporal technology lifecycle impact through EA-owned application/capability facts, receipt-bound foreign context evidence, governed remediation initiative, immutable target-state scenario membership, and append-only transformation state. Foreign product authority remains referenced rather than copied or promoted. The projector is read-only, preserves truth/evidence gates, and returns deterministic next actions for evidence completion, approval, execution, replanning, and target-state verification.';

COMMIT;
