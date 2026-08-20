BEGIN;

CREATE FUNCTION architecture_core.read_data_management_assessment_recheck_status(
    requested_tenant_record_id uuid,
    requested_recheck_request_id uuid
)
RETURNS TABLE (
    assessment_recheck_request_id uuid,
    data_management_assessment_projection_id uuid,
    successor_assessment_projection_id uuid,
    recheck_state_code text,
    successor_readiness_code text,
    successor_overall_score_basis_points integer,
    successor_missing_evidence_count integer,
    next_action text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  selected_request architecture_core.assessment_recheck_request%ROWTYPE;
  source_projection architecture_core.data_management_assessment_projection%ROWTYPE;
  successor_projection architecture_core.data_management_assessment_projection%ROWTYPE;
  missing_evidence_count integer;
BEGIN
  IF requested_tenant_record_id IS NULL
     OR requested_recheck_request_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant and assessment reassessment request are required';
  END IF;

  IF uuid_extract_version(requested_recheck_request_id) IS DISTINCT FROM 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment reassessment request id must be canonical UUIDv7';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  SELECT request_record.*
    INTO selected_request
    FROM architecture_core.assessment_recheck_request AS request_record
   WHERE request_record.tenant_record_id = requested_tenant_record_id
     AND request_record.assessment_recheck_request_id = requested_recheck_request_id;

  IF selected_request.assessment_recheck_request_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment reassessment request is unavailable for the verified tenant';
  END IF;

  SELECT projection_record.*
    INTO source_projection
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = requested_tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         selected_request.data_management_assessment_projection_id;

  IF source_projection.data_management_assessment_projection_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment reassessment request has no source assessment projection';
  END IF;

  SELECT projection_record.*
    INTO successor_projection
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = requested_tenant_record_id
     AND projection_record.supersedes_assessment_result_uri =
         source_projection.assessment_result_uri
   ORDER BY projection_record.recorded_at ASC
   LIMIT 1;

  IF successor_projection.data_management_assessment_projection_id IS NULL THEN
    RETURN QUERY
    SELECT
      selected_request.assessment_recheck_request_id,
      selected_request.data_management_assessment_projection_id,
      NULL::uuid,
      'awaiting_result'::text,
      NULL::text,
      NULL::integer,
      NULL::integer,
      'await_assessment_recheck'::text;
    RETURN;
  END IF;

  IF successor_projection.recorded_at < selected_request.recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment reassessment successor predates the reassessment request';
  END IF;

  SELECT pg_catalog.count(*)::integer
    INTO missing_evidence_count
    FROM architecture_core.assessment_missing_evidence_projection AS evidence_record
   WHERE evidence_record.tenant_record_id = requested_tenant_record_id
     AND evidence_record.data_management_assessment_projection_id =
         successor_projection.data_management_assessment_projection_id;

  IF successor_projection.readiness_code = 'evidence_complete'
     AND missing_evidence_count <> 0 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence-complete reassessment cannot retain missing evidence';
  END IF;

  IF successor_projection.readiness_code = 'evidence_gap'
     AND missing_evidence_count = 0 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence-gap reassessment must retain missing evidence';
  END IF;

  RETURN QUERY
  SELECT
    selected_request.assessment_recheck_request_id,
    selected_request.data_management_assessment_projection_id,
    successor_projection.data_management_assessment_projection_id,
    successor_projection.readiness_code,
    successor_projection.readiness_code,
    successor_projection.overall_score_basis_points,
    missing_evidence_count,
    CASE successor_projection.readiness_code
      WHEN 'evidence_gap' THEN 'plan_remaining_assessment_gap'
      WHEN 'evidence_complete' THEN 'close_assessment_improvement_loop'
      ELSE NULL
    END::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.read_data_management_assessment_recheck_status(uuid, uuid)
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
      'architecture_core.read_data_management_assessment_recheck_status(uuid,uuid) '
      'TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.read_data_management_assessment_recheck_status(
    uuid,
    uuid
) IS
'Purpose-bound tenant-scoped read for one assessment reassessment request. It joins only EA-owned projected evidence to the unique direct successor assessment and returns an explicit buyer next action without copying or mutating semantic-data-portal authority.';

COMMIT;
