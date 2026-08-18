BEGIN;

CREATE FUNCTION architecture_core.read_target_state_monitoring_status(
    requested_tenant_record_id uuid,
    requested_transformation_id uuid,
    requested_valid_at timestamptz,
    requested_recorded_at timestamptz,
    requested_max_evidence_age_days integer DEFAULT 90
)
RETURNS TABLE (
    architecture_transformation_id uuid,
    verification_state_code text,
    verification_effective_at timestamptz,
    verification_recorded_at timestamptz,
    evidence_record_id uuid,
    evidence_age_days integer,
    monitoring_state_code text,
    next_action text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  selected_state_code text;
  selected_effective_at timestamptz;
  selected_recorded_at timestamptz;
  selected_evidence_id uuid;
  selected_evidence_age_days integer;
BEGIN
  IF requested_tenant_record_id IS NULL
     OR requested_transformation_id IS NULL
     OR requested_valid_at IS NULL
     OR requested_recorded_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant, transformation, valid time, and recorded time are required';
  END IF;

  IF uuid_extract_version(requested_transformation_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state monitoring transformation id must be UUIDv7';
  END IF;

  IF requested_max_evidence_age_days NOT BETWEEN 1 AND 3650 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'maximum evidence age must be between 1 and 3650 days';
  END IF;

  PERFORM pg_catalog.set_config(
      'app.tenant_record_id',
      requested_tenant_record_id::text,
      true
  );

  SELECT
      history_record.transformation_state_code,
      history_record.effective_at,
      history_record.recorded_at,
      history_record.evidence_record_id
    INTO
      selected_state_code,
      selected_effective_at,
      selected_recorded_at,
      selected_evidence_id
    FROM architecture_core.transformation_history_record AS history_record
   WHERE history_record.tenant_record_id = requested_tenant_record_id
     AND history_record.architecture_transformation_id = requested_transformation_id
     AND history_record.transformation_state_code IN ('verified', 'gap_detected')
     AND history_record.effective_at <= requested_valid_at
     AND history_record.recorded_at <= requested_recorded_at
   ORDER BY
      history_record.sequence_number DESC,
      history_record.recorded_at DESC
   LIMIT 1;

  IF selected_state_code IS NULL OR selected_evidence_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target-state monitoring requires verification evidence at both requested cutoffs';
  END IF;

  selected_evidence_age_days := pg_catalog.floor(
      pg_catalog.extract(epoch FROM (requested_valid_at - selected_effective_at))
      / 86400
  )::integer;

  IF selected_evidence_age_days < 0 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'monitoring evidence cannot occur after the requested valid time';
  END IF;

  RETURN QUERY
  SELECT
      requested_transformation_id,
      selected_state_code,
      selected_effective_at,
      selected_recorded_at,
      selected_evidence_id,
      selected_evidence_age_days,
      CASE
        WHEN selected_state_code = 'gap_detected' THEN 'gap_detected'
        WHEN selected_evidence_age_days > requested_max_evidence_age_days THEN 'stale'
        ELSE 'current'
      END::text,
      CASE
        WHEN selected_state_code = 'gap_detected' THEN 'replan_target_state'
        WHEN selected_evidence_age_days > requested_max_evidence_age_days
          THEN 'collect_new_target_state_evidence'
        ELSE 'continue_monitoring'
      END::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.read_target_state_monitoring_status(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
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
      'architecture_core.read_target_state_monitoring_status('
      'uuid,uuid,timestamptz,timestamptz,integer) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.read_target_state_monitoring_status(
    uuid,
    uuid,
    timestamptz,
    timestamptz,
    integer
) IS
'Purpose-bound bitemporal read projection over terminal target-state verification evidence. It never changes transformation history: verified evidence is current or stale according to the caller policy, while gap_detected evidence routes the buyer back to replanning.';

COMMIT;
