BEGIN;

CREATE FUNCTION architecture_core.request_data_management_assessment_recheck_for_tenant(
    requested_tenant_record_id uuid,
    requested_assessment_projection_id uuid,
    requested_trigger_evidence_acceptance_id uuid,
    requested_decision_request_id uuid,
    requested_at timestamptz
)
RETURNS TABLE (
    assessment_recheck_request_id uuid,
    outbox_event_id uuid,
    next_action text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  previous_tenant_setting text;
  returned_recheck_id uuid;
  returned_outbox_id uuid;
  returned_next_action text;
BEGIN
  IF requested_tenant_record_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'tenant record id is required for reassessment';
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
    SELECT
        requested.assessment_recheck_request_id,
        requested.outbox_event_id,
        requested.next_action
      INTO returned_recheck_id, returned_outbox_id, returned_next_action
      FROM architecture_core.request_data_management_assessment_recheck(
        requested_assessment_projection_id,
        requested_trigger_evidence_acceptance_id,
        requested_decision_request_id,
        requested_at
      ) AS requested;
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

  RETURN QUERY
  SELECT
      returned_recheck_id,
      returned_outbox_id,
      returned_next_action;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.request_data_management_assessment_recheck_for_tenant(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz
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
      'architecture_core.request_data_management_assessment_recheck_for_tenant('
      'uuid,uuid,uuid,uuid,timestamptz) TO ea_runtime';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.request_data_management_assessment_recheck_for_tenant(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz
) IS
'Purpose-bound runtime command port for requesting a reassessment after the final projected data-management evidence gap is accepted. The verified tenant is installed only for the duration of the delegated command, the prior tenant setting is restored on success or failure, PUBLIC execution is revoked, and the underlying command remains the sole authority for idempotency, provenance, temporal integrity, and transactional outbox emission.';

COMMIT;
