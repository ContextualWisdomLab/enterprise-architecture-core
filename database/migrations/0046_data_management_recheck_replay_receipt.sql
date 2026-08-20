BEGIN;

-- The reassessment command has exact-replay semantics, but its original receipt
-- did not expose whether this invocation created durable evidence or replayed an
-- existing decision. Recreate the pre-release command ports with an explicit
-- boolean so HTTP clients can distinguish 201 creation from 200 exact replay.
DROP FUNCTION architecture_core.request_data_management_assessment_recheck_for_tenant(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz
);
DROP FUNCTION architecture_core.request_data_management_assessment_recheck(
    uuid,
    uuid,
    uuid,
    timestamptz
);

CREATE FUNCTION architecture_core.request_data_management_assessment_recheck(
    requested_assessment_projection_id uuid,
    requested_trigger_evidence_acceptance_id uuid,
    requested_decision_request_id uuid,
    requested_requested_at timestamptz
)
RETURNS TABLE (
    assessment_recheck_request_id uuid,
    outbox_event_id uuid,
    replayed boolean,
    next_action text
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  active_tenant_id uuid;
  source_projection architecture_core.data_management_assessment_projection%ROWTYPE;
  trigger_acceptance architecture_core.assessment_evidence_acceptance%ROWTYPE;
  existing_request architecture_core.assessment_recheck_request%ROWTYPE;
  existing_event_id uuid;
  trigger_causation_event_id uuid;
  trigger_next_action text;
  inserted_request_id uuid;
  inserted_event_id uuid;
BEGIN
  active_tenant_id := architecture_core.current_tenant_id();
  IF active_tenant_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant context is required for assessment reassessment';
  END IF;

  IF requested_assessment_projection_id IS NULL
     OR requested_trigger_evidence_acceptance_id IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_requested_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment, triggering acceptance, decision, and request time are required';
  END IF;

  IF uuid_extract_version(requested_assessment_projection_id) <> 7
     OR uuid_extract_version(requested_trigger_evidence_acceptance_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment reassessment identifiers must be UUIDv7';
  END IF;

  -- Serialize before replay inspection so a concurrent exact retry observes the
  -- first transaction's durable request/outbox pair rather than racing a unique
  -- constraint. Locking the immutable projection also keeps replay valid after a
  -- later supersession while different decisions remain conflicts.
  PERFORM 1
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = active_tenant_id
     AND projection_record.data_management_assessment_projection_id =
         requested_assessment_projection_id
   FOR UPDATE;

  SELECT recheck_record.*
    INTO existing_request
    FROM architecture_core.assessment_recheck_request AS recheck_record
   WHERE recheck_record.tenant_record_id = active_tenant_id
     AND recheck_record.decision_request_id = requested_decision_request_id;

  IF existing_request.assessment_recheck_request_id IS NOT NULL THEN
    IF existing_request.data_management_assessment_projection_id IS DISTINCT FROM
           requested_assessment_projection_id
       OR existing_request.trigger_evidence_acceptance_id IS DISTINCT FROM
           requested_trigger_evidence_acceptance_id
       OR existing_request.requested_at IS DISTINCT FROM requested_requested_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different reassessment meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = active_tenant_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.data_management.assessment_recheck_requested.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'assessment reassessment request exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_request.assessment_recheck_request_id,
      existing_event_id,
      true,
      'await_assessment_recheck'::text;
    RETURN;
  END IF;

  SELECT projection_record.*
    INTO source_projection
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = active_tenant_id
     AND projection_record.data_management_assessment_projection_id =
         requested_assessment_projection_id
     AND projection_record.superseded_at IS NULL
     AND projection_record.truth_status_code NOT IN ('superseded', 'rejected')
   FOR UPDATE;

  IF source_projection.data_management_assessment_projection_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'active assessment projection is unavailable for the verified tenant';
  END IF;

  SELECT acceptance_record.*
    INTO trigger_acceptance
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
    JOIN architecture_core.assessment_improvement_plan AS plan_record
      ON plan_record.tenant_record_id = acceptance_record.tenant_record_id
     AND plan_record.assessment_improvement_plan_id =
         acceptance_record.assessment_improvement_plan_id
   WHERE acceptance_record.tenant_record_id = active_tenant_id
     AND acceptance_record.assessment_evidence_acceptance_id =
         requested_trigger_evidence_acceptance_id
     AND plan_record.data_management_assessment_projection_id =
         requested_assessment_projection_id;

  IF trigger_acceptance.assessment_evidence_acceptance_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'triggering evidence acceptance does not belong to the assessment';
  END IF;

  IF EXISTS (
      SELECT 1
        FROM architecture_core.assessment_missing_evidence_projection AS missing_record
       WHERE missing_record.tenant_record_id = active_tenant_id
         AND missing_record.data_management_assessment_projection_id =
             requested_assessment_projection_id
         AND NOT EXISTS (
             SELECT 1
               FROM architecture_core.assessment_improvement_plan AS plan_record
               JOIN architecture_core.assessment_evidence_acceptance AS acceptance_record
                 ON acceptance_record.tenant_record_id = plan_record.tenant_record_id
                AND acceptance_record.assessment_improvement_plan_id =
                    plan_record.assessment_improvement_plan_id
              WHERE plan_record.tenant_record_id = missing_record.tenant_record_id
                AND plan_record.data_management_assessment_projection_id =
                    missing_record.data_management_assessment_projection_id
                AND plan_record.missing_evidence_code = missing_record.missing_evidence_code
         )
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment still has projected evidence gaps without accepted evidence';
  END IF;

  SELECT
      event_record.outbox_event_id,
      event_record.event_payload_json ->> 'next_action'
    INTO trigger_causation_event_id, trigger_next_action
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id = active_tenant_id
     AND event_record.decision_request_id = trigger_acceptance.decision_request_id
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1';

  IF trigger_causation_event_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'triggering evidence acceptance lacks transactional outbox provenance';
  END IF;

  IF trigger_next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'reassessment must bind to the evidence acceptance that causally closed the final gap';
  END IF;

  INSERT INTO architecture_core.assessment_recheck_request (
      tenant_record_id,
      data_management_assessment_projection_id,
      trigger_evidence_acceptance_id,
      decision_request_id,
      requested_at
  ) VALUES (
      active_tenant_id,
      requested_assessment_projection_id,
      requested_trigger_evidence_acceptance_id,
      requested_decision_request_id,
      requested_requested_at
  )
  RETURNING assessment_recheck_request.assessment_recheck_request_id
    INTO inserted_request_id;

  INSERT INTO architecture_core.outbox_event (
      tenant_record_id,
      aggregate_object_id,
      architecture_transformation_id,
      event_type_code,
      event_payload_json,
      event_schema_version,
      causation_event_id,
      decision_request_id
  ) VALUES (
      active_tenant_id,
      source_projection.subject_capability_object_id,
      NULL,
      'org.contextualwisdomlab.ea.data_management.assessment_recheck_requested.v1',
      pg_catalog.jsonb_build_object(
          'assessment_recheck_request_id', inserted_request_id,
          'data_management_assessment_projection_id',
              requested_assessment_projection_id,
          'trigger_evidence_acceptance_id',
              requested_trigger_evidence_acceptance_id,
          'assessment_result_uri', source_projection.assessment_result_uri,
          'next_action', 'await_assessment_recheck'
      ),
      '1.0.0',
      trigger_causation_event_id,
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_request_id,
    inserted_event_id,
    false,
    'await_assessment_recheck'::text;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.request_data_management_assessment_recheck(
    uuid,
    uuid,
    uuid,
    timestamptz
)
FROM PUBLIC;

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
    replayed boolean,
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
  returned_replayed boolean;
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
        requested.replayed,
        requested.next_action
      INTO
        returned_recheck_id,
        returned_outbox_id,
        returned_replayed,
        returned_next_action
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
      returned_replayed,
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

COMMENT ON FUNCTION architecture_core.request_data_management_assessment_recheck(
    uuid,
    uuid,
    uuid,
    timestamptz
) IS
'Purpose-bound reassessment command with explicit replay evidence. It serializes on the tenant-local immutable assessment projection so concurrent exact decisions converge on one durable request/outbox pair. A new decision returns replayed=false; an exact durable retry returns replayed=true. Conflicting meaning, incomplete evidence, invalid causation, and foreign tenant state fail closed. PUBLIC execution remains revoked.';

COMMENT ON FUNCTION architecture_core.request_data_management_assessment_recheck_for_tenant(
    uuid,
    uuid,
    uuid,
    uuid,
    timestamptz
) IS
'Purpose-bound runtime reassessment port. It installs the verified tenant only for the delegated command, restores prior tenant context on success or failure, preserves the underlying command replay signal, and exposes no direct application-table authority. PUBLIC execution is revoked and ea_runtime receives only this command when that role exists.';

COMMIT;
