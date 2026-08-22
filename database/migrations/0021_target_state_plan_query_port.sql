BEGIN;

-- The purpose-bound SECURITY DEFINER port must never inherit superuser or
-- BYPASSRLS authority from whichever deployment identity applies migrations.
-- Keep its owner non-login and non-inheriting so only the wrapper can exercise
-- the explicitly granted read surface below.
DO $$
BEGIN
  IF NOT EXISTS (
      SELECT 1
        FROM pg_catalog.pg_roles
       WHERE rolname = 'ea_function_owner'
  ) THEN
    CREATE ROLE ea_function_owner
      NOLOGIN
      NOINHERIT
      NOSUPERUSER
      NOCREATEDB
      NOCREATEROLE
      NOREPLICATION
      NOBYPASSRLS;
  END IF;
END;
$$;

ALTER ROLE ea_function_owner
  NOLOGIN
  NOINHERIT
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOREPLICATION
  NOBYPASSRLS;

-- PostgreSQL grants EXECUTE on newly created functions to PUBLIC by default.
-- Change the default for the actual migration identity, regardless of whether
-- the deployment calls it ea_owner, ea_app, or another dedicated owner role.
ALTER DEFAULT PRIVILEGES
REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

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
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant identity is required for target-state reads';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  RETURN QUERY
  SELECT *
    FROM architecture_core.project_technology_target_state_plan(
        requested_technology_version_id,
        assessment_valid_at,
        assessment_recorded_at,
        planning_horizon_days
    );
END;
$$;

ALTER FUNCTION architecture_core.read_technology_target_state_plan(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
)
OWNER TO ea_function_owner;

REVOKE ALL
ON FUNCTION architecture_core.read_technology_target_state_plan(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
)
FROM PUBLIC;

-- The non-login definer can read only the tables reached by the target-state
-- projection chain. FORCE ROW LEVEL SECURITY on tenant-owned tables remains in
-- effect because this role owns no application tables and has NOBYPASSRLS.
GRANT USAGE ON SCHEMA architecture_core TO ea_function_owner;
GRANT SELECT ON TABLE
    architecture_core.technology_version,
    architecture_core.architecture_relation,
    architecture_core.relation_type,
    architecture_core.technology_component,
    architecture_core.application_record,
    architecture_core.business_capability,
    architecture_core.lifecycle_interval,
    architecture_core.lifecycle_phase,
    architecture_core.architecture_transformation,
    architecture_core.remediation_initiative,
    architecture_core.architecture_scenario,
    architecture_core.application_context_projection,
    architecture_core.external_context_reference,
    architecture_core.projection_receipt,
    architecture_core.architecture_object,
    architecture_core.object_type,
    architecture_core.scenario_baseline,
    architecture_core.object_revision,
    architecture_core.scenario_object_delta,
    architecture_core.transformation_history_record
TO ea_function_owner;

GRANT EXECUTE ON FUNCTION
    architecture_core.current_tenant_id()
TO ea_function_owner;
GRANT EXECUTE ON FUNCTION
    architecture_core.project_technology_target_state_plan(
        uuid,
        timestamptz,
        timestamptz,
        integer
    ),
    architecture_core.project_technology_change_impact(
        uuid,
        timestamptz,
        timestamptz,
        integer
    ),
    architecture_core.project_application_context_impact(
        uuid,
        timestamptz,
        timestamptz
    ),
    architecture_core.project_scenario_objects_at(uuid, timestamptz),
    architecture_core.project_transformation_state(
        uuid,
        timestamptz,
        timestamptz
    )
TO ea_function_owner;

-- Migration 0020 creates this projector after deployment bootstrap may already
-- have revoked PUBLIC execution on the existing schema functions. PostgreSQL
-- grants EXECUTE on a newly created function to PUBLIC by default, so an
-- in-place upgrade would otherwise let ea_runtime bypass the purpose-bound
-- SECURITY DEFINER wrapper through its existing schema USAGE privilege.
REVOKE ALL
ON FUNCTION architecture_core.project_technology_target_state_plan(
    uuid,
    timestamptz,
    timestamptz,
    integer
)
FROM PUBLIC;

-- Repository migration rehearsals intentionally run before deployment-only
-- role bootstrap. Grant during an in-place upgrade only when the runtime role
-- already exists; clean installation re-establishes the same narrow grant in
-- database/init/003_grant_runtime_access.sql after the role is created.
DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM pg_catalog.pg_roles
       WHERE rolname = 'ea_runtime'
  ) THEN
    EXECUTE
      'GRANT EXECUTE ON FUNCTION '
      'architecture_core.read_technology_target_state_plan('
      'uuid,uuid,timestamptz,timestamptz,integer) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.read_technology_target_state_plan(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
) IS
'Purpose-bound SECURITY DEFINER read port owned by the non-login, NOBYPASSRLS ea_function_owner role. The service verifies Keyverse signature, issuer, audience, expiration, tenant, and role before passing the verified tenant UUID. The runtime role receives EXECUTE only on this wrapper and retains no direct table or projector authority.';

COMMIT;
