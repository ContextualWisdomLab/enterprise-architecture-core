BEGIN;

-- Verification states were added after the original target-state planner.
-- Keep the canonical buyer decision surface executable through the full
-- transformation lifecycle instead of degrading verified/gap states to the
-- unknown-state fallback.
CREATE OR REPLACE FUNCTION architecture_core.project_technology_target_state_plan(
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
      WHEN transformation_match.transformation_state_code = 'verified'
        THEN 'target_state_verified'
      WHEN transformation_match.transformation_state_code IN
           ('gap_detected', 'cancelled', 'rejected')
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
      WHEN transformation_match.transformation_state_code = 'verified'
        THEN 'monitor_target_state'
      WHEN transformation_match.transformation_state_code IN
           ('gap_detected', 'cancelled', 'rejected')
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
          SELECT
            projected_state.transformation_state_code,
            projected_state.effective_at,
            projected_state.recorded_at
            FROM architecture_core.project_transformation_state(
                active_transformation.architecture_transformation_id,
                assessment_valid_at,
                assessment_recorded_at
            ) AS projected_state
        ) AS transformation_state ON true
       ORDER BY
         transformation_state.effective_at DESC NULLS LAST,
         transformation_state.recorded_at DESC NULLS LAST,
         active_transformation.architecture_transformation_id DESC
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
'Projects the tenant-scoped Technology Change Impact and Target-State Planner through terminal verification: when multiple governed transformations share a scenario, the planner selects the latest bitemporally visible transformation state rather than an arbitrary transformation identifier; verified targets route through the evidence-freshness monitoring boundary before any continue-monitoring decision, while gap-detected, cancelled, or rejected targets route to governed replanning. The read-only projector preserves bitemporal cutoffs and foreign truth/evidence authority.';

-- Carry the scenario projector repair forward instead of rewriting migration 0012.
-- NULL is the current-system-time mode: only unsuperseded facts participate.
-- A historical cutoff admits facts recorded by that cutoff and facts superseded
-- only after it, preventing later-recorded deltas from leaking into as-of views.
CREATE OR REPLACE FUNCTION architecture_core.project_scenario_objects_at(
    requested_scenario_id uuid,
    requested_recorded_at timestamptz
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
     AND (
        architecture_scenario.superseded_at IS NULL
        OR architecture_scenario.superseded_at > requested_recorded_at
     )
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
     AND (
        architecture_scenario.superseded_at IS NULL
        OR architecture_scenario.superseded_at > requested_recorded_at
     )
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
       AND (
          scenario_object_delta.superseded_at IS NULL
          OR scenario_object_delta.superseded_at > requested_recorded_at
       )
       AND (
          requested_recorded_at IS NULL
          OR scenario_object_delta.recorded_at <= requested_recorded_at
       )
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

-- Carry the scenario projector repair forward instead of rewriting migration 0012.
-- NULL is the current-system-time mode: only unsuperseded facts participate.
-- A historical cutoff admits facts recorded by that cutoff and facts superseded
-- only after it, preventing later-recorded deltas from leaking into as-of views.
CREATE OR REPLACE FUNCTION architecture_core.project_scenario_objects_at(
    requested_scenario_id uuid,
    requested_recorded_at timestamptz
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
     AND (
        architecture_scenario.superseded_at IS NULL
        OR architecture_scenario.superseded_at > requested_recorded_at
     )
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
     AND (
        architecture_scenario.superseded_at IS NULL
        OR architecture_scenario.superseded_at > requested_recorded_at
     )
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
       AND (
          scenario_object_delta.superseded_at IS NULL
          OR scenario_object_delta.superseded_at > requested_recorded_at
       )
       AND (
          requested_recorded_at IS NULL
          OR scenario_object_delta.recorded_at <= requested_recorded_at
       )
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

COMMIT;
