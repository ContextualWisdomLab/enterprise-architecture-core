BEGIN;

CREATE FUNCTION architecture_core.read_technology_target_state_plan(
  requested_tenant_record_id uuid,
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
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
  IF requested_tenant_record_id IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'verified tenant identity is required for target-state reads';
  END IF;
  PERFORM pg_catalog.set_config('app.tenant_record_id', requested_tenant_record_id::text, true);
  RETURN QUERY SELECT * FROM architecture_core.project_technology_target_state_plan(
      requested_technology_version_id, assessment_valid_at, assessment_recorded_at, planning_horizon_days);
END;
$$;

REVOKE ALL ON FUNCTION architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer) FROM PUBLIC;

-- Migration 0020 creates this projector after deployment bootstrap may already
-- have revoked PUBLIC execution on existing functions. PostgreSQL grants newly
-- created functions to PUBLIC by default, so revoke the underlying projector
-- explicitly to preserve the purpose-bound SECURITY DEFINER boundary on upgrade.
REVOKE ALL ON FUNCTION architecture_core.project_technology_target_state_plan(uuid,timestamptz,timestamptz,integer) FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'ea_runtime') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.read_technology_target_state_plan(uuid,uuid,timestamptz,timestamptz,integer) IS
'Purpose-bound SECURITY DEFINER read port for the authenticated EA service. The service verifies Keyverse signature, issuer, audience, expiration, tenant, and role before passing the verified tenant UUID. The runtime role receives EXECUTE only on this wrapper and retains no direct table or projector authority.';

COMMIT;
